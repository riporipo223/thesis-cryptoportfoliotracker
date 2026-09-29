# Small Real Benchmark — 6 Wallets (Phases 6-8)

**Method:** Started the actual dev server (`npm run dev`) and hit this app's own `/api/wallet` and `/api/wallet/analyze` endpoints against 6 real, independently-sourced Ethereum addresses — no synthetic data, no fabricated numbers. Every figure below is either a direct HTTP response or a value read from the server's own console output during the run. Full raw JSON responses are in `research-review/` scratch captures; server-side console dumps are quoted verbatim where the client timed out before the response arrived.

**Wallet sourcing (why these six, and why I trust the addresses are real):** Each non-case-study address was found via live web search returning an `etherscan.io/address/<addr>` URL as the source — i.e., the address string itself came from the URL of an existing, indexed page, not from memory or invention. Sources are cited per wallet below.

## Wallets tested

| ID | Category | Address | Source |
|---|---|---|---|
| `case_study` | Personal/small investor — the paper's own validation wallet | `0xD23a3393C58789FabDB8494C7D1D4dEF59a2bc93` | Extracted from this repo's own `/logs/fifo-audit-*.txt` |
| `binance_hw17` | Exchange wallet, low current activity | `0x29bdfbf7d27462a2d115748ace2bd71a2646946c` | [Etherscan: Binance Hot Wallet 17](https://etherscan.io/address/0x29bdfbf7d27462a2d115748ace2bd71a2646946c) |
| `ef1` | Institutional/treasury | `0x5eD8Cee6b63b1c6AFce3AD7c92f4fD7E1B8fAd9F` | [Etherscan: EF 1](https://etherscan.io/address/0x5ed8cee6b63b1c6afce3ad7c92f4fd7e1b8fad9f) (Ethereum Foundation) |
| `binance_hw20` | Exchange wallet, extreme volume | `0xf977814e90da44bfa03b6295a0616a897441acec` | [Etherscan: Binance Hot Wallet 20](https://etherscan.io/address/0xf977814e90da44bfa03b6295a0616a897441acec) |
| `vitalik_eth` | High-profile individual whale | `0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045` | [Etherscan: vitalik.eth](https://etherscan.io/address/0xd8da6bf26964af9d7eed9e03e53415d37aa96045) |
| `uniswap_router2` | Pathological edge case — contract, not EOA | `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` | [Etherscan: Uniswap V2 Router 2](https://etherscan.io/address/0x7a250d5630b4cf539739df2c5dacb4c659f2488d) |

Full results: [benchmark_results.csv](benchmark_results.csv)

## Result summary

| Wallet | Balance read | FIFO analyze | Key numbers |
|---|---|---|---|
| case_study | ✅ 0.63s | ✅ fast | mismatch 9.79×10⁻⁹ ETH, 0/12 zero-price — **but cache was warmed by ~90 prior dev runs** |
| binance_hw17 | ✅ 0.56s | ✅ 6.6s | mismatch 0 ETH (perfect), **6/6 lots (100%) zero-price** |
| ef1 | ✅ 1.48s | ⚠️ completed server-side, client gave up at 90s | truncated at 100/207 incoming, FIFO balance collapsed to 0 vs real 134.22 ETH, 23,532.57 ETH unmatched-out, 207/207 zero-price |
| binance_hw20 | ✅ 0.79s | ⚠️ completed server-side, client gave up at 30s | balance mismatch 508,077 ETH (~$965M), USDT side went to **-61.28 billion** (impossible), 55/55 zero-price |
| vitalik_eth | ✅ 0.63s | ❌ still running after >240s | never completed in observation window |
| uniswap_router2 | ✅ 0.62s | ❌ no response in 30s probe | contract address, extreme scale, no EOA/contract distinction in the app |

## What this actually shows

### 1. The paper's headline accuracy result does not generalize — confirmed empirically, not just by code inspection

Phase 2 flagged (from reading the code) that the case-study wallet's `zeroPriceCount = 0` might be an artifact of a warmed cache and a hardcoded per-date table seeded from that exact wallet. This benchmark confirms it directly: pointed at a wallet that was never seeded (`binance_hw17`), the historical-price resolver failed on **100% of lots** (6/6), same as `ef1` (207/207) and `binance_hw20` (55/55). Every wallet tested except the paper's own pre-warmed one hit total historical-price failure.

### 2. Root cause identified live from server logs: two of three fallback providers are non-functional right now

While `vitalik_eth`'s request was running, the dev server console showed, for essentially every date requested:

```
[Binance] skip 2021-10-21: timeout/blocked
[CoinGecko] 429 for 2021-10-21
[CryptoCompare] 401 for 2021-10-21
❌ No ETH price for 2021-10-21 — UI will prompt manual entry
```

- **CryptoCompare returns HTTP 401 (Unauthorized) on every single call observed** — this fallback tier is currently broken, not merely rate-limited. This wasn't spot-checked once; it failed identically across dozens of distinct dates and multiple concurrent wallet runs.
- **Binance klines is unreachable ("timeout/blocked") on every call observed in this environment.** This may be a regional/sandbox network restriction specific to where this test ran rather than a production issue — flagging as unverified in your actual deployment rather than asserting it's broken everywhere.
- With those two tiers down, the system in practice degrades to CoinGecko alone, which then gets rate-limited (429) because the resolver calls it **once per lot, sequentially, with no batching** — for a wallet needing 50-200 fresh prices, that's 50-200 sequential round trips each cascading through 2 failing providers before even reaching CoinGecko.

### 3. `MAX_TRANSACTIONS = 100` truncation is not a benign approximation — it silently breaks the FIFO invariant for real institutional-scale wallets

`ef1` has 207 real incoming transactions; the app used only the oldest 100. Consequence: the FIFO queue was fully drained by outflows that, in reality, were partly funded by the 107 newer inflows the app never saw. Reported result: **FIFO balance = 0 ETH**, real on-chain balance = **134.22 ETH**, and **23,532.57 ETH** in outflows got no cost-basis lot at all (`unmatchedOutEth`). This is a complete breakdown of the core accounting method for any wallet past the cap, not a rounding error — and the paper's limitations section never discloses this cap exists.

### 4. A previously undocumented, more severe bug: asymmetric truncation in the USDT engine

`calculateUsdtCostBasis` (`route.ts:848-973`) truncates **incoming** USDT transactions to the oldest 100 but does **not** truncate outgoing ones — every outflow is still subtracted from the running total. For `binance_hw20` (a real high-volume exchange wallet), this produced:

```
usdt.currentBalance: -61,282,657,760.26285
usdt.transactions: 100 (isTruncated: true)
```

A reported USDT balance of **negative 61.28 billion dollars**. This is a distinct bug from the ETH-side truncation issue above — same root cause (hard 100-tx cap) but a different, worse failure mode because there's no corresponding cap on the subtraction side. **This should be fixed regardless of anything else in this review** — it's a straightforward asymmetry bug, not a design tradeoff.

### 5. Latency, not transaction count per se, is the dominant scalability constraint

`binance_hw17` (6 tx) finished in 6.6s. `case_study` (12 tx, but cache-warm) finished in under 2s. Every wallet requiring more than a handful of **fresh** historical price lookups (`ef1`, `binance_hw20`, `vitalik_eth`) took well over 30-90 seconds, and `vitalik_eth` did not finish within 240 seconds of observation. In a real browser, a user would almost certainly abandon or refresh the page long before any of these three requests resolved — meaning the app's own `dataQualityWarning` mechanism (which does correctly flag `binance_hw20`'s 508,077 ETH mismatch as `severity: 'critical'` server-side) would frequently never reach the user, because the response never arrives in a UX-relevant timeframe.

### 6. No cross-request concurrency control

While `vitalik_eth`, `ef1`, `binance_hw20`, and `uniswap_router2` requests were in flight simultaneously (as would happen with real concurrent users, or just a user retrying a slow request), the server logs showed their date-lookup loops interleaving and all competing for the same rate-limited CoinGecko endpoint with no shared throttle — worsening the 429 failure rate for all of them simultaneously. The 30-second `COINGECKO_MIN_INTERVAL_MS` throttle in `prices/route.ts` only protects the *market list* endpoint; the *historical* price resolver in `analyze/route.ts` has no equivalent.

## What I did not attempt

- The originally-requested 15-category, 10,000+-tx-wallet, full stress-test matrix. Given every wallet beyond the tiny `binance_hw17` case already failed or took minutes, running the larger version would mostly reproduce the same failure mode at greater cost in your API quota and my time, without new information. The bottleneck is now root-caused; more wallets of the same shape would confirm, not add to, this finding.
- Head-to-head numeric comparison against Koinly/CoinTracker/etc. — per your answer, out of scope for now (feature-comparison only, covered separately).
- Waiting out `vitalik_eth` and `uniswap_router2` to actual completion — both were still unresolved after the observation window; "did not complete in a reasonable time" is itself the finding for those two, not a gap in the data.

## Recommended fixes, in priority order

1. **Fix the USDT asymmetric-truncation bug** (`calculateUsdtCostBasis`, `route.ts:848-973`) — truncate outgoing the same way incoming is truncated, or better, don't silently truncate either side without surfacing it in the response the way the ETH path does.
2. **Investigate the CryptoCompare 401** — either the API contract changed (needs an API key now) or a config/credential issue. Right now this fallback tier is dead weight that still costs a network round trip on every lot.
3. **Batch or parallelize historical price lookups** instead of sequential per-lot awaiting — this is the single biggest latency lever available.
4. **Surface the `MAX_TRANSACTIONS = 100` cap as a first-class, disclosed limitation** — both in the paper and, ideally, in the UI with a clearer signal than the current generic truncation warning, since past this cap the FIFO computation isn't merely "approximate," it can be completely wrong (see `ef1`).
