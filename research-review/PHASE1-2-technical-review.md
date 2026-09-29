# Technical Review of "Pengembangan Aplikasi Web Pelacakan Portofolio Aset Kripto dengan Cost Basis FIFO"

**Reviewer stance:** adversarial code-vs-claim verification. Every claim below was checked against the actual source in `/Users/ripo/crypto-portfolio` as it exists today (not the paper's description of it, not comments, not README). File:line citations are given so you can re-check independently.

**Target venue as submitted:** JIKO (Jurnal Informatika dan Komputer) — a SINTA-indexed Indonesian national journal, not Scopus/IEEE/Springer/Elsevier-indexed. This matters for Phase 14 later; noted here so the rest of the review is calibrated to the right bar.

---

## PHASE 1 — System Understanding (grounded in source)

### 1.1 Actual architecture

The paper's claimed "three-tier architecture" is real but looser than the diagram implies — it's Next.js API routes acting as a thin server tier, no separate service layer, no database beyond Firestore.

```
┌─────────────────────────────┐
│  Presentation (Next.js App Router, client components)   │
│  app/dashboard, app/portfolio, app/wallet, app/integrated│
└───────────────┬───────────────────────────────────────┘
                │ fetch()
┌───────────────▼───────────────────────────────────────┐
│  API Routes (app/api/**)  — server-only, holds secrets  │
│  • /api/wallet            → ETH/USDT balance (Alchemy)  │
│  • /api/wallet/analyze    → FIFO cost-basis engine       │
│  • /api/solana/balance    → SOL/SPL balance (Helius)     │
│  • /api/prices            → market price list (CoinGecko)│
└───────────────┬───────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────┐
│  External services                                       │
│  Alchemy (ETH JSON-RPC) · Helius (SOL JSON-RPC)          │
│  Etherscan (tx history) · CoinGecko/Binance/CryptoCompare│
│  /Coinbase/Kraken (price, 3 independent fallback chains) │
│  Firebase Auth + Firestore (users, manual assets, wallets)│
└─────────────────────────────────────────────────────────┘
```

Key modules and what they actually do:

| Module | File | Role |
|---|---|---|
| FIFO cost-basis engine | [app/api/wallet/analyze/route.ts](app/api/wallet/analyze/route.ts) | Fetches Etherscan tx history, runs FIFO lot queue, drains gas, reconciles vs on-chain balance |
| Audit report writer | [app/api/wallet/analyze/audit.ts](app/api/wallet/analyze/audit.ts) | Renders the FIFO run as a terminal table + `/logs/fifo-audit-*.txt` file |
| ETH/USDT balance reader | [app/api/wallet/route.ts](app/api/wallet/route.ts) | Raw `eth_getBalance` / `eth_call(balanceOf)` via Alchemy, own 5-tier live-price fallback |
| SOL/SPL reader | [lib/solana.ts](lib/solana.ts) | Helius `getBalance` / `getTokenAccountsByOwner`, no FIFO |
| Market price feed | [app/api/prices/route.ts](app/api/prices/route.ts) | CoinGecko batch, own separate fallback chain |
| Aggregation | [lib/hooks/usePortfolioAggregator.ts](lib/hooks/usePortfolioAggregator.ts) | Pure client-side sum of manual (Firestore) + wallet (ETH/USDT only — BTC and SOL excluded) |

`lib/web3/` — an empty directory. Whatever module the paper's Fig. 2 implies lives there doesn't exist as a separate abstraction; the logic is inlined directly in the API route handlers.

### 1.2 What the FIFO engine actually does (ground truth, not the paper's description)

1. Fetches `txlist`, `txlistinternal`, and USDT `tokentx` from Etherscan (`route.ts:168-198`).
2. Builds a FIFO purchase queue from **all** incoming ETH txs — `MAX_TRANSACTIONS = 100` oldest are actually queued; beyond that the response is silently marked `isTruncated` (`route.ts:14, 429-433`).
3. Each incoming lot gets a historical price via a **6-tier resolver**: in-memory cache → file cache (`lib/price-cache.json`) → a **hardcoded per-date table** → Binance klines → CoinGecko history → CryptoCompare (`route.ts:1031-1141`).
4. Outgoing txs consume the queue oldest-first; if the queue empties before the OUT amount is satisfied, the shortfall is logged as `unmatchedOutEth` (`route.ts:652-672`).
5. **Gas fee drain**: every self-signed tx (normal, non-internal) has `gasUsed × gasPrice` computed and consumed from the FIFO queue as if it were an outflow (`route.ts:676-724`). This is real and is the mechanism behind the paper's central claim.
6. **Undisclosed fallback accounting method**: if after all of the above the FIFO-remaining balance still exceeds the on-chain balance by more than 0.0001 ETH, the engine does **not** report a mismatch — it silently switches to a Weighted-Average-Cost (WAC) reconciliation that rescales every remaining lot's quantity by `onChainBalance / fifoRemaining` and recomputes cost basis from the blended average price (`route.ts:726-752`, `audit.ts:191-199`). This is a second, different accounting method than FIFO, invoked conditionally, and it is nowhere described in the paper's Section 2.4.
7. USDT uses a much simpler path: no gas handling (correct, gas is paid in ETH not USDT), no price resolution (hardcoded `$1.00`), no WAC fallback (`route.ts:848-973`).

### 1.3 Price/fallback architecture — three independent implementations, not one

The paper (§2.1, §2.4) describes a single "Resolver Harga Historis" with cache → primary → fallback. In the code there are **three separate, independently written fallback chains**, each with a different provider order and different last-resort behavior:

| Pipeline | File | Order | Last resort |
|---|---|---|---|
| Historical price (FIFO lots) | `route.ts:1031-1141` | memory → file cache → hardcoded table → Binance klines → CoinGecko → CryptoCompare | `requiresManualPrice` flag, cost = $0 |
| Live ETH price (Wallet page) | `app/api/wallet/route.ts:114-271` | CoinGecko → Coinbase → Kraken → Firestore cache → memory | **hardcoded `$2500`** ("Conservative estimate") |
| Market list (Dashboard) | `app/api/prices/route.ts:100-268` | CoinGecko (30s throttled) → per-coin Binance → CryptoCompare → memory | coin silently omitted from response |

This is a real fallback architecture and it is genuinely more resilient than a naive single-provider call — that part of the novelty claim holds. But it is not the single unified component the paper's architecture diagram implies, and the `$2500` hardcoded ETH default in `wallet/route.ts:256` is a real, disclosed-to-nobody data-quality risk: if every live source fails for an active wallet, the UI will silently show a portfolio value computed off a stale hardcoded constant rather than surfacing an error.

### 1.4 Evidence the FIFO audit is real and reproducible

`/logs/fifo-audit-*.txt` contains ~90 real timestamped runs from 2026-05-11 through 2026-07-12, each a genuine FIFO reconstruction against live Etherscan data for what appears to be the same wallet used in the paper's case study. This is good — it means the empirical claim in the paper is not fabricated; the mechanism that produces it exists and runs repeatedly. The most recent log I inspected (`fifo-audit-2026-07-12T03-20-39-838Z.txt`) shows gas total `0.038161 ETH` and cost basis `$24.48` — both close to but **not identical** to the paper's reported `0.037908 ETH` / `$25.24` (Table 4), which is expected since the wallet has continued transacting and historical prices get re-resolved between runs — but it confirms the number in the paper is a snapshot of a live, moving measurement, not a fixed synthetic fixture.

---

## PHASE 2 — Claim-by-Claim Verification

Legend: ✅ Supported · ⚠️ Partially supported / needs caveat · ❌ Not supported / contradicted by code.

| # | Claim (paraphrased from paper) | Supported? | Where in code | Evidence | Severity if wrong |
|---|---|---|---|---|---|
| 1 | System unifies manual portfolio + on-chain data in one interface | ✅ | `usePortfolioAggregator.ts:71-135`, `app/integrated/page.tsx` | Hook sums Firestore manual assets + wallet ETH/USDT into one `IntegratedSummary` | — |
| 2 | FIFO engine reconstructs purchase lots from incoming txs, consumes oldest-first on outgoing | ✅ | `route.ts:508-674` | Literal FIFO queue (`purchases.shift()`), oldest-first consumption confirmed | — |
| 3 | Gas fees are accounted for in balance reconciliation | ✅ | `route.ts:676-724` | Every self-signed non-internal tx's `gasUsed*gasPrice` is drained from the FIFO queue | — |
| 4 | Historical price resolved via layered cache → primary → fallback providers | ⚠️ | `route.ts:1031-1141` | Real, but chain includes a **hardcoded per-date table seeded from this exact wallet's prior audit runs** (comment: "Covers all lots in this wallet so FIFO never hits zeroPriceCount=0", `route.ts:1005-1006`) — not a generic mechanism, tuned to the case study | **High** — the paper's "0 zero-price-count" result is partly guaranteed by hand-entered data for this specific wallet, not purely emergent from the described fallback design. This is a circularity risk in the one empirical validation the paper reports. |
| 5 | Missing-price lots retained with `requiresManualPrice` flag, balance stays consistent | ✅ | `route.ts:554-598` | Confirmed; cost = $0, quantity still added to balance | — |
| 6 | Three-tier architecture (presentation / API logic / external services) | ✅ (loosely) | file layout | Real, but "Mesin FIFO", "Resolver Harga Historis" etc. described as discrete components are inlined functions in a single 1141-line route file, not separate modules; `lib/web3/` (implied by the architecture description) is empty | Low — architecture description is idealized/simplified for the diagram, common in papers, but slightly overstates modularity |
| 7 | Read-only, no wallet-connect, no private keys | ✅ | entire codebase — no signing library imported, only address-based reads (`eth_getBalance`, `eth_call`, Etherscan `txlist`) | Confirmed no `personal_sign`/wallet-connect/private-key handling anywhere | — |
| 8 | FIFO scope limited to Ethereum; Solana shown balance-only, no FIFO | ✅ | `lib/solana.ts` has no lot/queue logic at all, only balance reads | Confirmed | — |
| 9 | Price updates every 60 seconds via polling | ⚠️ | Not verified in the files read — this is a client-side polling interval, likely in a dashboard component not yet inspected | Needs confirmation from `app/dashboard/page.tsx` before treating as settled | Medium — unverified, flag for follow-up |
| 10 | Case study wallet: 107 tx, 12 incoming (lots), 7 outgoing, balance mismatch 1.46×10⁻⁹ ETH, gas 0.037908 ETH, cost basis $25.24 | ⚠️ | mechanism confirmed real via `/logs/fifo-audit-*.txt`, but exact figures are a single timestamped snapshot from a continuously-live wallet | The audit mechanism producing these numbers is genuine and reproducible (not fabricated), but N=1, and the numbers drift run-to-run as new transactions post and prices get re-resolved (2026-07-12 run: gas 0.038161 ETH, cost basis $24.48 — different from the paper's reported figures). The paper presents a single moving measurement as a fixed result without stating the capture date/block. | **Medium** — not fabrication, but a reproducibility/methodology gap: another reviewer re-running against the same address today would get different numbers and might wrongly conclude the system is non-deterministic or the paper is wrong, when actually the wallet itself changed. |
| 11 | "Cost basis dapat dirunut hingga lot dan transaksi asalnya" (cost basis traceable to originating lot/transaction) — stated as the system's key differentiator vs. competitors | ❌ (conditionally) | `route.ts:726-752` | This is true **only when the WAC fallback does not trigger**. When it does, lot quantities are rescaled by a blended factor and cost basis is recomputed from a scaled average — traceability to the *original* transaction's actual price is broken for every open lot at that point, contradicting the auditability claim made in §4 (Discussion) as the system's distinguishing feature. | **High** — this directly undermines the paper's stated novelty differentiator (auditability/traceability), and the condition under which it breaks (bridge/internal transfers not captured by Etherscan) is exactly the kind of wallet behavior common in "DeFi user" or "bridge user" categories the paper's own future-work section calls for testing. |
| 12 | System handles wallets robustly / "large wallet detected" truncation is a known, disclosed limitation | ⚠️ | `route.ts:14, 429-433, 331-333` | Real cap of 100 incoming transactions; response is marked `isTruncated` with a UI warning, but this hard limit is **not mentioned anywhere in the paper's Batasan (limitations) section** — only network scope (ETH/SOL only) and cost-basis-method scope (FIFO only) are disclosed as limitations | Medium — a real, user-facing accuracy boundary that the paper doesn't disclose, relevant to any claim of generalizability beyond the 107-tx case study |
| 13 | Dashboard/Integrated reconciliation: $315.83 vs $314.36, difference fully explained by SOL + SPL exclusion on Integrated | ✅ | `usePortfolioAggregator.ts:94-96, 127-129` | Hook explicitly excludes SOL from `walletETH`/`walletUSDT` sums (`// Wallet: ETH and USDT only`), consistent with the paper's explanation | — |
| 14 | Black-box test table (Table 3) — all 8 scenarios "Lolos" | ⚠️ | Not independently re-run | The scenarios map to real code paths that exist (auth via Firebase, manual asset CRUD via Firestore, ETH/USDT read via `wallet/route.ts`, SOL/SPL read via `lib/solana.ts`, FIFO via `analyze/route.ts`, missing-price flag, 60s poll unverified). Existence of a code path is not the same as a rerun test result — I have not exercised the UI to reproduce "Lolos" independently. | Medium — plausible given the code exists, but the paper reports this as an executed test, not a code-path audit; I can't currently confirm the black-box results were literally observed as written without running the app |
| 15 | Novelty: simultaneous integration of (a) manual+on-chain unification, (b) automated FIFO from blockchain reconstruction, (c) gas-fee-aware reconciliation | ✅ mechanically / ⚠️ as a *novelty* claim | all of the above | All three mechanisms are real and present together. Whether this combination is actually *novel* relative to existing commercial tools (Koinly, CoinTracker, Rotki all already do exactly this — on-chain FIFO/HIFO with gas-fee-aware balance reconciliation, at production scale, across dozens of chains) is a **research-gap validity question**, not a code-verification question — see Phase 3 note below. | **High for the paper's core contribution claim** — this needs to be addressed honestly in Phase 3, not skipped |

### Immediate red flags worth fixing before this goes further in review

1. **Undisclosed WAC fallback breaks the stated auditability differentiator** (#11). Either disclose it explicitly in §2.4 as a secondary reconciliation method with its own limitation, or the auditability claim in the Discussion needs to be qualified ("traceable to source lot except when on-chain balance cannot be reconciled from tracked lots alone").
2. **Hardcoded per-wallet price table casts doubt on the single validation result** (#4, #10). Zero-price-count = 0 is a headline pass criterion in Table 4; if it's partly guaranteed by hand-seeded prices for this one address, that needs disclosure, or the validation needs to be re-run on a wallet whose prices were never hand-seeded.
3. **100-transaction hard cap is undisclosed** (#12) and directly limits how far the paper's "future work: test more diverse wallets" can go without hitting silent truncation.

---

## What I have NOT verified yet (and why)

- **Novelty claim vs. Koinly/CoinTracker/Rotki/CoinStats/etc. (Phase 3)** — I have general knowledge of these products' feature sets but have not logged into any of them to compare live outputs; I don't have accounts, and creating them is outside what I'll do without your explicit request (and even then, live financial-account creation on third-party services needs your sign-off).
- **Literature gap analysis (Phase 4)** — doable properly, but needs live web search against IEEE/Springer/Elsevier/ACM/Scopus indices rather than my training-data recall, since the point is to find *current, real, verifiable* citations, not plausible-sounding ones.
- **Live multi-wallet benchmark (Phases 6-8)** — technically possible: `.env.local` has real Alchemy, Helius, and Etherscan keys configured. But running this at the scale requested (15 behavior categories, wallets up to 10,000+ tx, stress testing) means dozens to hundreds of live API calls against free-tier quotas, real wall-clock time, and the `MAX_TRANSACTIONS=100` cap (finding #12 above) means most "whale"/"active trader" wallets will silently truncate rather than produce a meaningful stress test unless I also patch that constant for the test run.
- **Head-to-head comparison vs. commercial software (Phase 9)** — not feasible without accounts on Koinly/CoinTracker/etc., which I won't create on your behalf per the platform's rules on account creation. If you already have accounts and want to hand me exported CSVs to diff against this app's output, that's a different, very doable task.
- **Paper rewrite / journal-fit verdict (Phases 12-14)** — straightforward once we've settled what Phases 3-11 are actually going to contain, since the verdict depends on what gets fixed.

## Recommended next step

Given the genuine constraints above, I'd suggest sequencing the rest rather than trying to do all 12 remaining phases in one pass. The three findings under "immediate red flags" are the ones that most affect whether the paper's central claims hold up — worth deciding whether to fix the code, fix the paper's disclosure, or both, before spending effort on benchmark datasets and literature reviews built on top of an unresolved auditability gap.
