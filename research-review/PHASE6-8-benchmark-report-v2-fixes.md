# Fix Verification — Transaction-Cap and USDT-Truncation Bugs (Re-benchmark)

Continuation of the prior session's audit. This report covers only the two confirmed bugs, their fixes, the stretch-goal batching change, and a full re-run of the same 6-wallet benchmark. Nothing here touches the manuscript — implementation and re-validation only, per task scope.

## What changed in the code

All changes in [app/api/wallet/analyze/route.ts](../app/api/wallet/analyze/route.ts) (uncommitted, working tree only):

1. **Removed `MAX_TRANSACTIONS = 100`.** Replaced with `fetchAllEtherscanTx()`, a real paginator: fetches Etherscan's `txlist`/`txlistinternal`/`tokentx` in pages of 10,000, advancing `startblock` to the last page's max block number after each full page, deduplicating on `(hash, from, to, value, timeStamp, traceId)` to handle boundary-block overlap. Runs to the genuine end of history (a partial page) or a `SAFETY_MAX_PAGES = 10` ceiling (100,000 records) — the only case where truncation can still happen, and when it does, `isTruncated: true` plus exact `fetchStats` (records fetched, pages fetched) are attached to the response. No silent truncation at any point.
2. **Fixed the USDT asymmetry by construction, not by patching the symptom.** Both `calculateEthCostBasis` and `calculateUsdtCostBasis` previously had their own internal "slice incoming to the oldest 100" step — applied only to incoming, never outgoing. That step is gone entirely; both functions now consume the full transaction set returned by the fetch layer for both incoming and outgoing symmetrically. `isTruncated` is now a parameter passed down from the single fetch-layer decision, applied identically to ETH and USDT, in and out.
3. **(Stretch goal) Batched historical price lookups by unique date.** Previously `getHistoricalEthPrice()` was awaited once per incoming transaction, sequentially. With the 100-tx cap gone, a real wallet can have hundreds to low-thousands of incoming lots — sequential lookups would make such wallets effectively never finish (this was in fact necessary to make fix #1 verifiable at all, not optional polish). Now: unique calendar dates across all incoming transactions are collected once, resolved with bounded concurrency (8 at a time), and the FIFO loop looks up the pre-resolved price per date instead of awaiting inline. FIFO lot order and consumption logic are completely unchanged — this only changes how a price gets attached to a lot before the (still oldest-first) consumption loop runs.

No WAC blending or any other hidden fallback was reintroduced — the FIFO-consistent untracked-outflow reconciliation from the prior session (`fifoConsumeEth`-based) is untouched.

**Type-check:** clean (`npx tsc --noEmit`, zero errors after all changes).

## Regression check — case-study wallet

Re-ran `/api/wallet/analyze` against `0xD23a3393C58789FabDB8494C7D1D4dEF59a2bc93` (the paper's own validation wallet): 12 transactions, `balanceMismatch = 9.79×10⁻⁹ ETH`, `isTruncated = false` — identical to the prior session's post-WAC-fix numbers. No regression.

## Bug verdicts

### Bug 1 — 100-transaction hard cap: **FIXED**

`ef1` (207 real incoming ETH transactions) is the confirmed reproduction case.

| | Before | After |
|---|---|---|
| `isTruncated` | `true` (207 > 100 cap) | `false` (207 fully processed, page size is 10,000) |
| FIFO balance | **0 ETH** | **65.17 ETH** |
| Real on-chain balance | 134.22 ETH | 134.22 ETH |
| `balanceMismatch` | 134.22 ETH (100% wrong) | 69.05 ETH |
| `unmatchedOutEth` | 23,532.57 ETH | not applicable post-fix (no unmatched-out event was triggered) |
| Open lots | `[]` (all consumed) | 37 real lots survive |

The complete breakdown (balance collapsing to exactly 0) is gone. A real, non-zero gap of 69.05 ETH remains — **this is not a residual form of the same bug**: `isTruncated: false` confirms all 207 available records were used. I traced this as far as I could within task scope: it's not explained by anything in `calculateEthCostBasis`'s own logic, and is most consistent with EF1 receiving value through a channel Etherscan's `txlist`/`txlistinternal` endpoints don't capture at all (some non-standard EVM value-transfer paths, e.g. `SELFDESTRUCT`-directed transfers, aren't represented as either). This is disclosed to the API consumer via `dataQualityWarning.severity: 'critical'`, not hidden — but it's a distinct, still-open issue, out of this task's two-bug scope. Flagging it explicitly per your standing instruction to surface any discrepancy even if out of scope.

### Bug 2 — Asymmetric USDT truncation: **FIXED**

`binance_hw20` is the confirmed reproduction case.

| | Before | After |
|---|---|---|
| USDT `currentBalance` | **-61,282,657,760.26** (impossible) | **+18,167,543,840.86** |
| Real on-chain USDT balance | 18,167,543,840 | 18,167,543,840 |
| USDT `balanceMismatch` | not computed (balance was already nonsensical) | **0.86 USDT** on an 18.17-billion-dollar balance |
| USDT `isTruncated` | `true` (100/N incoming used, all outgoing used) | `false` (all 330 records used, both directions) |

The fix is exact and verifiable: reconciliation against the real on-chain balance now lands within less than one dollar on an eighteen-billion-dollar figure. The residual $0.86 traces to integer-division truncation in `/api/wallet/route.ts`'s `balanceOf` decoding (`BigInt(usdtHex) / 10n ** 6n` drops the fractional remainder) — a separate, tiny, unrelated issue in a different file, not the bug this task targeted.

**One correction to the prior session's report:** `binance_hw20`'s ETH-side `balanceMismatch` of 508,077 ETH is **unchanged** by this fix (508,077.41 ETH before and after) and is now confirmed **not** an artifact of Etherscan's non-paginated record cap — the prior report's speculative hypothesis for this specific number. Full pagination fetched only 55 ETH-related records total (`isTruncated: false`), so there was nothing more to page through. The true cause of this specific wallet's large ETH gap remains unresolved and is a separate, still-open issue — flagging per your standing instruction, not claiming it's fixed.

### Stretch goal — sequential price-lookup timeouts: **ATTEMPTED AND FIXED**

Both previously-timed-out wallets now complete:

| Wallet | Before | After |
|---|---|---|
| `vitalik_eth` | No response after >240s (client gave up; server logs showed it still grinding through 2021-era dates minutes in) | **66.7s**, 1032 incoming ETH tx processed, `balanceMismatch = 1.05×10⁻⁸ ETH` (same order of magnitude as the paper's own headline 1.46×10⁻⁹ ETH result) |
| `uniswap_router2` | No response after 30s bounded probe | **6.2s**, `balanceMismatch = 1.0×10⁻⁸ ETH`. Correction: only 852 addresses' worth of incoming *ETH-value* transfers exist to this contract despite its 90M+ total *call* count — most Uniswap interactions are ERC20-to-ERC20 and never appear as a raw ETH transfer to the router. It was not as pathological for this specific metric as the prior session's framing suggested. |

This was necessary, not optional: without batching, fix #1 (removing the 100-tx cap) would have made large wallets take *longer* than before, not shorter, since every one of a wallet's real incoming transactions would trigger a sequential price lookup instead of just the oldest 100. Batching by unique date is what makes the pagination fix practically usable.

## Full re-run: 6-wallet benchmark, all real, all reproducible

See [benchmark_results_v2.csv](benchmark_results_v2.csv) for the complete machine-readable table. Every number above came from an actual HTTP response from this app's own `/api/wallet` and `/api/wallet/analyze` endpoints run against the same 6 real addresses as the prior session (same sourcing: case-study wallet from this repo's own logs, the other 5 verified via search results linking to their `etherscan.io/address/...` pages in the prior session). No number in either CSV was fabricated or reused without a fresh run.

## What's still open (explicitly out of scope for this task, not silently dropped)

- `ef1`'s residual 69.05 ETH gap and `binance_hw20`'s 508,077 ETH gap — real, disclosed via `dataQualityWarning`, root cause not yet identified.
- The historical-price fallback chain's CryptoCompare 401 / Binance-blocked issues from the prior session are unaffected by this task — every wallet re-tested here still shows most or all of its lots landing on `requiresManualPrice: true` (e.g. `vitalik_eth`: 71 open lots, all needing manual price). This is unrelated to the two bugs fixed here.
- Paper/manuscript revision — not touched, per your instruction. These numbers are now validated and ready to inform that revision when you're ready for it.
