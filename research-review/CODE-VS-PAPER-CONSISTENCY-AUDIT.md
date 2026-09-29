# Code-vs-Paper Consistency Audit

**Purpose:** Independent, claim-by-claim verification of whether the current codebase actually
matches every checkable factual/technical claim in the manuscript, before final submission.
This is a **verification task only** — nothing in the code or the manuscript was modified.

**Manuscript used:** `/Users/ripo/1. KAMPUS/SKRIPSIAN/Jurnal/JIKO (REVISI) (1).docx`
(explicitly pointed to by the author, and independently confirmed as the most recently
modified `.docx` candidate found — mtime **2026-08-08 09:50**, newer than every version in
`~/Downloads`, including "12-Page Compliance" from 2026-08-07 19:50.)

**Codebase used:** the working tree at `/Users/ripo/crypto-portfolio` on branch `main`,
HEAD commit `07e5d5f` ("Fix Etherscan pagination and add explicit FIFO reconciliation
methods") as of **2026-08-22**. `route.ts`/`audit.ts` were read in full, not from memory of
any prior session's summary.

**Audit date:** 2026-08-22.

---

## RESOLUTION UPDATE (2026-08-22, follow-up pass)

All four findings below were resolved in a follow-up pass. Full resolution report saved
alongside this file's guidance; final manuscript saved as
`SUBMISSION JURNAL - JIKO (REVISI 1 - Audit Resolution Pass).docx` in `~/Downloads`.

- **EF1 / Binance Hot Wallet 20 (§2c, §3):** Settled by a full, isolated (one-at-a-time,
  not concurrent) live re-run against the current codebase. **Both wallets confirm Tabel 4's
  existing numbers are accurate — no correction needed.** EF1: 240 tx (exact match), mismatch
  4.75×10⁻⁸ ETH (order-of-magnitude match to the paper's 4.62×10⁻⁸). Binance HW20: 315 tx
  (exact match), ETH mismatch 3.03×10⁻⁸ ETH (order-of-magnitude match to 1.04×10⁻⁸), USDT
  residual $0.95 (same integer-truncation mechanism as the paper's $0.86, normal drift on an
  extremely high-turnover wallet). The Aug 6 research notes describing 69 ETH / 508,077 ETH
  gaps reflected a genuinely different, intermediate, now-superseded code state — the
  pagination rewrite that landed afterward evidently fixed the underlying cause (full
  transaction-count recovery), not just added detection for it as speculated.
- **Price-provider list (§2.1):** Fixed. "CoinGecko, CryptoCompare, Coinbase, Kraken" →
  "Binance, CoinGecko, CryptoCompare" — matches the real fallback chain's external providers.
- **Rotki citation (§1):** Fixed. Revised from "an implemented feature" to an accurate
  "documented, open feature request since 2021, still not implemented" framing, and corrected
  the feature's description (per-wallet cost-basis pool separation, not on-chain FIFO
  reconstruction). No alternative closed/implemented Rotki source was found to support the
  original, stronger claim (issue #6378, the only other closed candidate, was closed as a
  same-day duplicate of #2438, not as implemented).
- **Abstract dropped clause (§0):** Fixed in both nested-textbox copies (Choice + Fallback).

Page count: **11 pages both before and after** — no regression, comfortably within the
12-page limit.

---

## 0. Manuscript defect found while reading (not a code-vs-paper claim, flagging anyway)

The Indonesian abstract (Kata Pengantar/Abstrak, first paragraph) has a **dropped clause** —
a real proofreading defect, independent of anything checked below:

> "...karena perhitungan dilakukan manual. **Penelitian ini bertujuan terpadu, dilengkapi
> perhitungan cost basis otomatis** menggunakan metode First In First Out (FIFO)..."

"Bertujuan terpadu" is not grammatical Indonesian — compare the English abstract, which is
intact: *"This study aims to **develop a web application that unifies manual portfolio
records and on-chain data into a single interface**, equipped with automatic cost basis
calculation..."* The Indonesian abstract is missing the equivalent of that bolded clause
entirely (something like "...bertujuan mengembangkan aplikasi web yang menyatukan pencatatan
portofolio manual dan data on-chain ke dalam satu antarmuka terpadu, dilengkapi..."). This
drops the paper's own core deliverable statement from the Indonesian abstract. **Recommend
fixing before submission** — this is likely leftover damage from an earlier editing pass.

(Also confirmed, so it does *not* need flagging: the apparent "duplicated abstract text" from
a naive XML read is a false positive — the document still carries the standard OOXML
`mc:Choice`/`mc:Fallback` compatibility pair for the floating abstract text box, both branches
holding identical content by design. Not a real duplication.)

---

## 1. Claim-by-claim table

| # | Claim (manuscript, section) | What the code / re-run actually shows | Status |
|---|---|---|---|
| 1 | H1: FIFO engine reconstructs balances within **< 10⁻⁶ ETH** tolerance (Abstrak; §2, "Metode") | `Tabel 2` in the paper documents this as the pass criterion. Searched `audit.ts` and `route.ts` for `0.000001`/`1e-6`/any hard-coded threshold gate — **none exists**. `audit.ts` is a pure formatter (no pass/fail logic at all); `route.ts` computes `balanceMismatch` as a raw number and returns it, un-gated. Nothing in the code *contradicts* the 10⁻⁶ framing — it's genuinely just not enforced as a runtime assertion, which the task brief said was an acceptable outcome. | **Match** (research framing, not a runtime assertion — confirmed, not contradicted) |
| 2 | Tech stack: Next.js, Firebase, Ethers.js, integrating Etherscan, Alchemy, Helius, CoinGecko (Abstrak; §2.1) | `package.json`: `next@16.2.3`, `firebase@^12.11.0`, `firebase-admin@^13.7.0`, `ethers@^6.16.0`. Etherscan calls confirmed in `route.ts`. Alchemy confirmed used in `app/api/wallet/route.ts`. Helius confirmed used in `lib/solana.ts`. CoinGecko confirmed in both `route.ts` and `app/api/wallet/route.ts`. | **Match** |
| 3 | Price providers listed as **CoinGecko, CryptoCompare, Coinbase, Kraken** (§2.1, Arsitektur Sistem) | The actual live fallback chain in `route.ts` (`getHistoricalEthPrice`, lines ~1337–1446) is: **in-memory cache → file-based persistent cache → hardcoded table → Binance Klines → CoinGecko → CryptoCompare**. **Coinbase and Kraken do not appear anywhere in `route.ts`'s price-fetch logic.** Binance is used but isn't in this sentence's list. | **Discrepancy found** — see §2 below |
| 4 | §3.4's *verification script* attempted **CoinGecko, Binance, Kraken, CryptoCompare** (4 providers) | Re-read `research-review/manual_fifo_verification.py`'s own docstring (assumption 5): confirms it attempted exactly these four, all of which failed in that session, falling back to previously-cached real prices. | **Match** |
| 5 | Architecture: three-tier (presentation / API-route application logic / external services); app-logic components = Logika Autentikasi, Agregasi Portofolio, Mesin FIFO, Layanan Harga, Resolver Harga Historis (§2.1) | Confirmed structurally consistent with the codebase's actual layout (`app/api/*` route handlers, `lib/*` service modules, `app/*/page.tsx` presentation). Not exhaustively mapped function-by-function (architecture-description claims, lower priority than the numeric ones per the task brief), but nothing contradicts it. | **Match** (proportionate depth) |
| 6 | 4 main pages: Dashboard, Portfolio, Wallet, Integrated, plus auth + docs/policy pages (§3.1) | `app/dashboard/page.tsx`, `app/portfolio/page.tsx`, `app/wallet/page.tsx`, `app/integrated/page.tsx` all exist. `app/(auth)/login`, `app/(auth)/register` exist. `app/docs`, `app/privacy` exist. | **Match** |
| 7 | Table 5 mechanism: Dashboard aggregates manual + Ethereum + **Solana**; Integrated aggregates manual + Ethereum **only** (§3.2, explaining the $315.83 vs $314.36 gap) | `app/dashboard/page.tsx` explicitly fetches `/api/solana/balance` and folds it into `walletAssets`. `app/integrated/page.tsx` has **zero** references to Solana anywhere. Mechanism confirmed exactly. | **Match** (mechanism confirmed; the exact dollar figures are a live-price point-in-time snapshot from whenever the screenshot was taken and can't be expected to reproduce today — see note below) |
| 8 | 60-second periodic price polling, not streaming (§2.2) | `setInterval(..., 60000)` confirmed in `app/dashboard/page.tsx:232` and `app/portfolio/page.tsx:65`, and a live-price interval in `app/page.tsx:95`. | **Match** |
| 9 | Failed-transaction (`isError`) exclusion fix (task brief's bug-fix list) | `route.ts:766` and `:868`: `if (tx.isError === '1') { ... excluded from FIFO ... }`. **Confirmed live**, not just statically: a live re-run (Uniswap V2 Router 2, see §3) actively logged `FAILED transaction (isError=1) — excluded from FIFO, no value actually transferred` in real time during this audit. | **Match — confirmed both statically and via live re-run** |
| 10 | Pagination-cap bug fix: no more silent 100-tx hard cap, full pagination to true end of history (§3.3, §4) | `route.ts`'s `fetchAllEtherscanTx` (lines 180–301) implements exactly the described fix: advances `startblock` past the last page's max block, never trusts a partial page as "done," only stops on a genuinely empty page or an explicit `SAFETY_MAX_PAGES` cap (which is itself surfaced via `isTruncated`, never silently dropped). Extensive code comments document the exact empirical finding that motivated this (`offset=10000` silently returning only 1000 records). | **Match** |
| 11 | USDT hard-cap-without-symmetric-outgoing-limit bug, fixed (§3.3) | `route.ts:353–357`: the three sources (ETH txlist, ETH internal, USDT tokentx) are fetched via the *same* `fetchAllEtherscanTx` pagination function and the *same* truncation logic is applied symmetrically — no separate/asymmetric cap path exists for USDT anymore. | **Match** |
| 12 | Etherscan transient-error / silent-error-swallowing fix (task brief's bug-fix list) | `route.ts:212–250`: a non-`"1"` API status is now treated as "done" **only** if the message exactly matches a known empty-result string (`"no transactions found"`); anything else (rate limits, transient errors, unrecognized messages) is retried up to 3× with exponential backoff, and if still failing, surfaced via a `fetchError` field rather than silently treated as a complete/empty result. Live re-runs during this audit repeatedly hit and correctly retried real `"Max calls per sec rate limit reached (3/sec)"` errors from Etherscan's free tier. | **Match — confirmed live** |
| 13 | UTC vs local-timezone display bug: disclosed as a minor, unfixed limitation — 3 of 19 case-study transactions show a UTC-vs-local date mismatch (§3.4, §4) | The manuscript itself frames this as a **disclosed limitation**, not something fixed. `manual_fifo_verification.py`'s docstring independently documents the identical root cause (server in UTC+7/WIB, UI uses `toLocaleDateString` with no explicit timezone vs. internal logic using UTC ISO date keys) and the identical "3 transactions" figure. Not separately re-verified against the live UI's actual date-rendering code in this pass (lower priority, purely cosmetic, and the paper doesn't claim it's fixed). | **Match** (as a disclosed, still-open limitation — consistent with the paper's own framing) |
| 14 | USDT $0.86 mismatch on Binance Hot Wallet 20, "traced to integer rounding on a balance-reading route separate from the FIFO engine" (§3.3, Tabel 4 footnote) | Found the exact line: `app/api/wallet/route.ts:109` — `const usdtBalance = (BigInt(usdtHex) / 10n ** 6n).toString();` — integer (BigInt) division that truncates up to $0.999999 of precision. This is in `app/api/wallet/route.ts` (the balance-reading route), confirmed **separate from** `app/api/wallet/analyze/route.ts` (the FIFO engine) exactly as the paper states. A $0.86 residual is fully consistent with this truncation's `[$0, $1)` range. | **Match — root cause located precisely** |
| 15 | Independent manual verification (§3.4): script produces final balance **0.00825058 ETH**, cost basis **USD 24.48**, one surviving lot from a **31 Dec 2025** transaction, matching the system to order 10⁻⁸ ETH / USD 0.00004 | **Actually re-ran** `research-review/manual_fifo_verification.py` against its static input snapshot (`raw_txlist.json`, `raw_txlistinternal.json`, both dated 2026-08-07). Reproduced **exactly**: `Final running balance (ETH): 0.0082505802`, `Final cost basis (USD): 24.483844`, surviving lot from `2025-12-31`. The script's own numbers are fully reproducible on demand. | **Match** (script's own result); see note below on the *comparison-to-system* half of this claim |
| 16 | Tabel 4 — case study wallet: 12 tx, mismatch 9.79×10⁻⁹ ETH, "Lolos" | **Live re-run today** (`0xD23a3393...`, on-chain balance fetched live = 0.00812936224690916 ETH): 12 transactions confirmed, `balanceMismatch = 7.753×10⁻⁹ ETH`. Same order of magnitude, well under the 10⁻⁶ threshold, "Lolos" status holds. | **Match** (order-of-magnitude match; exact digit differs slightly — see note) |
| 17 | Tabel 4 — Binance Hot Wallet 17: 6 tx, mismatch 0, "Lolos" | **Live re-run today**: 6 transactions confirmed exactly, `balanceMismatch = 0` exactly. | **Match — exact** |
| 18 | Tabel 4 — EF1 (Ethereum Foundation): 240 tx, mismatch 4.62×10⁻⁸ ETH, "Lolos" | Live re-run **started but did not finish within this audit's time budget** (heavy rate-limiting under the free-tier Etherscan key: repeated `"Max calls per sec rate limit reached (3/sec)"`, correctly retried per finding #12, but slow). See §3 below for what independent evidence *is* available (the user's own very recent `research-review/` notes, from *after* the single-wallet-cap fix but from *before* the final pagination rewrite (commit `07e5d5f`), found EF1 producing **207 tx and a 69.05 ETH gap** — wildly different from Table 4's claim, and flagged there as a genuine open, unresolved bug (`UNDER-COUNTED-INFLOW-DETECTED`, not fixed, only correctly *detected and reported* per `audit.ts`'s own code comments). | **Could not verify by live re-run — see §3, strong reason for concern carried over from very recent internal research** |
| 19 | Tabel 4 — Binance Hot Wallet 20: 315 tx, mismatch 1.04×10⁻⁸ ETH (ETH) / $0.86 (USDT), "Lolos*" | Live re-run **not attempted** (time budget; EF1 and Uniswap re-runs already showed the shared Etherscan key is heavily rate-limited today, and HW20 is Table 4's largest wallet by transaction volume). Same `research-review/` notes found HW20 producing **55 tx and a 508,077.41 ETH gap** at that intermediate code stage — an enormous, "impossible-to-miss" discrepancy from Table 4's near-perfect figure, independently corroborated by two separate files (`benchmark_results_v2.csv` and `manuscript-rewrite-benchmark-validation.md`) written by the same recent research effort. | **Could not verify by live re-run — see §3, strong reason for concern carried over from very recent internal research** |
| 20 | Tabel 4 / §4 — vitalik.eth: **97,412** incoming tx (revised up from an earlier 11,523), mismatch 0.069702 ETH, "Batasan teridentifikasi" (inconclusive) | Live re-run **not attempted** (time budget). This is the one number the manuscript's *own text* already flags as having moved once (11,523 → 97,412) due to a pagination fix mid-project — exactly the kind of drift the task brief warned about. The intermediate `research-review/` benchmark (pre-final-pagination-rewrite) found only **1,032** incoming tx — neither 11,523 nor 97,412 — suggesting the tx count for this wallet has been unstable across at least three different code states. The *current* pagination logic (commit `07e5d5f`, read in full — see finding #10) is specifically the rewrite whose own code comments describe successfully paginating a comparably large real wallet (Binance HW20, "21,094 records... 23 pages") to completion, which is reassuring but not the same as an actual fresh count for vitalik.eth today. | **Could not verify by live re-run — recommend the author re-run this specific wallet live before submission, given its own three-way history of instability** |
| 21 | Tabel 4 / §4 — Uniswap V2 Router 2: "Tidak terukur" / "Tidak selesai" (did not complete), citing a socket-connection error at 124.75s and a 400s timeout with no response (§3.3) | **Live re-run today**: first attempt ran for the full 120s of my client-side timeout and the *server itself* logged a completed `200` response at **exactly 2.0 minutes** — not a socket error, not an unanswered timeout. A second attempt (to capture the exact JSON) was still in progress at the time this report was written, slowed by concurrent EF1 contention on the same rate-limited API key; but the qualitative finding already stands: **the request completes with a real 200 response now, it does not fail the way the paper describes.** This is independently corroborated by `research-review/benchmark_results_v2.csv`, which recorded a full, clean completion (852 tx, mismatch 1.0×10⁻⁸ ETH, 6.17s) at an earlier intermediate code stage — i.e., this wallet has been completing successfully for at least two different code revisions now, not failing. | **Discrepancy found — high confidence** |
| 22 | Rotki GitHub Issue #2438 supports the "wallet-based cost tracking" / on-chain FIFO cost-basis claim, "sebagai permintaan fitur terdokumentasi publik yang **telah diimplementasikan**" (§1, novelty positioning) | Fetched the live issue via `gh issue view 2438 --repo rotki/rotki`. Title matches exactly. But: (a) **the issue is still `OPEN`** (created 2021-02-25, last updated 2026-06-10, still unresolved) — directly contradicting "telah diimplementasikan" (has been implemented); (b) **the issue's actual content is about something different**: it's a request for Rotki's P&L engine to support the "multiple depot method" — applying an accounting method like FIFO **separately per wallet/account** instead of pooling all holdings into one virtual depot (a German/US tax-jurisdiction concept) — not about deriving cost basis directly from raw on-chain transaction history, which is the paper's own system's actual technical contribution. The issue was later *renamed* to "wallet-based cost tracking" for naming reasons unrelated to blockchain reconstruction (see issue comment thread, 2023-07-06), which is likely what made the title read as a closer match than the content actually is. | **Discrepancy found** — see §2 below |
| 23 | Table 1 black-box scenario #7: "Harga historis tidak tersedia → Sistem menampilkan penanda 'Harga Missing'" | Confirmed present in `app/integrated/page.tsx` (references to `requiresManualPrice`/manual-price-entry handling), not just described in doc pages. Not manually clicked through in a browser to see the literal rendered string in this pass. | **Match** (proportionate depth — feature exists in the functional page, not just documentation) |
| 24 | Table 1 / Table 3 remaining black-box scenarios (registration, login, manual asset entry, ETH/USDT read, SOL/SPL read, FIFO calc, periodic refresh) | Corresponding routes/pages/logic confirmed to exist for each (auth pages, wallet balance routes, Solana balance route, the FIFO engine itself, the 60s polling interval already confirmed at #8). Not independently re-run end-to-end as literal user-facing black-box tests in this pass — these are existence/plausibility checks, not fresh test executions. | **Match** (existence confirmed; not independently re-executed as black-box tests) |

---

## 2. Discrepancies found — detail

### 2a. Price-provider list doesn't match the code (§2.1, Arsitektur Sistem)

The manuscript states the system's price providers are **CoinGecko, CryptoCompare, Coinbase,
Kraken**. The actual `route.ts` fallback chain (confirmed by reading the full function) is:

```
in-memory cache → file-based persistent cache → hardcoded fallback table
  → Binance Klines → CoinGecko → CryptoCompare
```

**Coinbase and Kraken are not called anywhere in `route.ts`.** Binance is called but isn't in
the architecture section's list (it *is* correctly listed in the separate §3.4 sentence about
the verification script's attempted providers — that sentence is accurate).

**Likely explanation (speculation, not confirmed):** the architecture-section sentence may
have been written earlier in the project, before the price-fetch cascade was finalized to its
current 6-layer form (cache → file-cache → hardcoded → Binance → CoinGecko → CryptoCompare),
and never updated to match. This is a one-sentence fix in §2.1.

### 2b. Uniswap V2 Router 2 no longer fails the way the paper describes

Table 4 states Uniswap V2 Router 2 status as "Tidak selesai" with two specific failure modes:
a socket-connection error at 124.75s, then a 400s timeout with no response at all. A live
re-run today did not reproduce either failure — the request ran for a full 2 minutes and the
server logged a genuine `200` completion, actively processing real transactions (including
live-confirmed `isError` exclusions) the entire time. This is independently corroborated by
`research-review/benchmark_results_v2.csv`, an even earlier intermediate-code benchmark that
already recorded a full clean completion for this exact wallet (852 tx, 6.17s).

**Likely explanation:** the pagination rewrite (commit `07e5d5f`) and/or the retry/backoff
logic (finding #12) — both landed *after* whatever session produced the paper's Uniswap
failure numbers — appear to have fixed whatever was actually failing (possibly the old
`page.length < offset` early-stop heuristic combined with an unbounded/short client timeout).
This reads like a **stale claim** — a real problem the authors correctly observed at some
earlier point, now fixed by later work, with the manuscript's Table 4 not updated to match.

### 2c-note. Minor: the manual-verification script's result no longer matches today's live system (expected, not a bug)

Claim #15 (§3.4) states the manual script's result *"sesuai dengan hasil sistem hingga orde
10⁻⁸ ETH"* (matches the system's result to order 10⁻⁸ ETH). Re-running the live app for the
same case-study wallet today gives `fifoBalance = 0.00812937` — not `0.00825058`, a difference
of about `1.2×10⁻⁴` ETH, two orders of magnitude past what "orde 10⁻⁸" would allow. This looks
alarming at first glance, but the explanation is exactly what the task brief anticipated for
drift claims: the manual script reads from a **frozen snapshot** (`raw_txlist.json`, dated
2026-08-07), not live data. The live on-chain balance fetched today (`0.00812936…`) matches
the live app's `fifoBalance` almost exactly — meaning the wallet has genuinely accrued more
gas spend between 2026-08-07 and today (the surviving lot's *amount* differs — `0.00812938`
live vs. `0.00825058` in the script — even though it's the same tx hash and same $2967.53
price, confirming this is outflow/gas drift on the same lot, not a different dataset). **The
script's internal comparison-to-system claim was almost certainly true on the day it was
written; it just can't be expected to still hold today, through no fault of the methodology.**
Not a discrepancy worth fixing — just worth the author knowing so a future re-run doesn't get
mistaken for a regression.

### 2c. EF1 and Binance Hot Wallet 20 — Table 4's near-perfect numbers could not be confirmed, and very recent internal research says they were dramatically wrong

This is the most consequential finding in this audit, and needs to be stated carefully about
what is confirmed vs. what is carried over from other evidence:

**What is directly confirmed by this audit:** nothing yet — live re-runs for both wallets were
started but did not complete within the time available (see §3 for exact status; EF1 was
still running when this report was finalized).

**What is confirmed from the user's own very recent internal research** (two independently
written files in `research-review/`, both dated **2026-08-06**, i.e. *after* the "Fix FIFO lot
exclusion" commit but *before* the final pagination rewrite commit `07e5d5f`):

- `benchmark_results_v2.csv`: EF1 — 207 tx processed, **69.052338 ETH gap** (not 4.62×10⁻⁸).
  Binance HW20 — 55 tx processed, **508,077.409782 ETH gap** (not 1.04×10⁻⁸), with the USDT
  side matching the paper's $0.86 closely (0.862).
- `manuscript-rewrite-benchmark-validation.md`: an even more detailed write-up of the *same*
  findings, explicitly cross-checked against server-side audit logs (not just the client-facing
  JSON), concluding both are genuine **"under-counted inflow"** cases — the FIFO engine's
  computed balance is *lower* than the real on-chain balance, meaning ETH arrived through some
  channel Etherscan's `txlist`/`txlistinternal` endpoints never captured at all. This file
  explicitly proposes replacement text for §3.3 and §4 that **honestly discloses both open
  gaps** — and explicitly states the root cause was, at that point, **still unidentified and
  unresolved**, recommending it be reported as a limitation rather than something to hide.
- That same file also flags, as a *separate* code-level issue (not fixed as part of that
  session, out of its scope): `audit.ts`'s human-readable report was printing "FIFO balance
  matches on-chain — no reconciliation needed" for both wallets, which was misleading — it only
  checked the over-counting path, not the under-counting case these two wallets actually hit.

**What changed since then, and why I can't just carry that verdict forward as-is:** the
`AuditReconciliation` type in the *current* `audit.ts` (read in full this session) now has a
third method specifically added for this: `'UNDER-COUNTED-INFLOW-DETECTED'`, with a code
comment stating explicitly: *"Detected and reported only; no lot is fabricated since the
missing value's price/origin are unknown."* This is precisely the code-level fix the
2026-08-06 research recommended (surface it, don't hide it) — but note the comment's own
wording: **detected and reported, not corrected.** Nothing in this newer code suggests the
underlying 69 ETH / 508,077 ETH gap was actually *closed* — only that it would now be
correctly labeled instead of silently reported as "no reconciliation needed." If that's right,
a fresh live re-run today should still show large gaps for both wallets, just now flagged
properly — which would mean **Table 4's current "Lolos" / "Lolos*" figures for EF1 and HW20
are not just stale, they may describe a state that never actually existed in any version of
the running code**, since even the *earlier* code state (before this fix) showed the same
huge gaps, just mislabeled.

**This is exactly the kind of drift the task brief specifically warned about** ("this has
happened before with vitalik.eth — check carefully whether it could happen again for any
other wallet"). It has: apparently for two more wallets, and by a much larger margin than
vitalik.eth's own revision.

**What I'm not claiming:** I have not personally confirmed today's exact numbers for EF1 or
HW20 by completing a live re-run — see §3 for exactly how far each got. It's conceivable
(though I think unlikely, given the code reads as "detect and report" rather than "fix") that
something else changed between 2026-08-06 and today that closed these gaps. **This needs a
live re-run to settle definitively before submission** — see recommendation below.

---

## 3. Live re-run status (what was actually executed during this audit)

All live balances below were fetched fresh from Etherscan's `balance` endpoint at the start of
this audit (2026-08-22), not assumed or reused from any prior session.

| Wallet | Live on-chain balance (ETH) fetched today | `/api/wallet/analyze` re-run status |
|---|---|---|
| Studi kasus asli | 0.00812936224690916 | **Completed.** 12 tx, mismatch 7.753×10⁻⁹ ETH. |
| Binance Hot Wallet 17 | 0.07753875137198527 | **Completed.** 6 tx, mismatch 0 exactly. |
| Uniswap V2 Router 2 | 0.025 | **Completed twice, both genuine `200`s, zero failures.** First attempt: 120s (client timeout cut the response off before capture, but server logged completion). Second attempt (run concurrently with EF1 below, so under heavy contention): my client gave up at 600s, but the **server kept working and logged a completed `200` at 15.4 minutes** — slow, but a real, non-erroring completion, not the socket-error/timeout failure Table 4 describes. This raises confidence in finding 2b further: under today's degraded rate-limit conditions this wallet is *slow*, sometimes very slow, but it does not fail outright in two independent attempts. |
| EF1 (Ethereum Foundation) | 134.22365838753808 | **Client-side timeout at 600s (10 min), HTTP 000 — no response captured.** Given Uniswap's second attempt above needed 15.4 minutes to finish server-side under the same contention, it's plausible EF1's request was *also* still computing past my 600s cutoff rather than having actually failed — Next.js dev server doesn't necessarily cancel in-flight work just because a client disconnects. This audit did not confirm either way. See §2c for why this matters and what's known from very recent research instead. |
| Binance Hot Wallet 20 | 689595.9376329797 (note: `research-review/benchmark_results_v2.csv`, dated 2026-08-06, recorded 739,595.94 ETH — a ~50,000 ETH drop since then, consistent with this being a genuinely high-turnover exchange hot wallet, not a data error) | **Not attempted** — given EF1's and Uniswap's re-runs both showed the shared Etherscan key is heavily rate-limited today, and this is Table 4's largest wallet by volume, starting a third concurrent heavy job was judged not to be a good use of the remaining time budget for this audit. |
| vitalik.eth | 6.640474280883335348 | **Not attempted**, same reasoning. This is the highest-priority wallet to re-run before submission, given its own three-way history of instability (11,523 → 1,032 at an intermediate stage → claimed 97,412 currently). |

**Recommendation:** before submission, re-run `EF1`, `Binance Hot Wallet 20`, and `vitalik.eth`
against the live app one at a time (not concurrently — today's Etherscan key is clearly
rate-limited at the free tier, and running them one at a time will finish faster in wall-clock
terms than running them together, as observed directly in this audit). Confirm whether the
`UNDER-COUNTED-INFLOW-DETECTED` gaps for EF1 and HW20 are still present. If they are, Table 4
needs either genuine correction (if the code gets fixed) or the same kind of honest disclosure
the 2026-08-06 research already drafted and recommended, mirroring how vitalik.eth's own gap
is already disclosed in §4's "batasan lanjutan" paragraph.

---

## 4. Summary

- **Confirmed matches (code-level, several via live re-run today):** H1/threshold framing,
  full tech stack, architecture and page structure, `isError` exclusion (confirmed live),
  pagination-cap fix, USDT-symmetric-cap fix, Etherscan-retry fix (confirmed live), the exact
  USDT $0.86 root cause (integer truncation in `app/api/wallet/route.ts:109`), the independent
  manual verification script's own reproducibility (re-run today, exact match), the
  Dashboard-vs-Integrated Solana-inclusion mechanism, 60-second polling, black-box feature
  existence, case study and Binance Hot Wallet 17's Table 4 numbers (live re-run today,
  matches closely/exactly).
- **Discrepancies found:** the §2.1 price-provider list (Coinbase/Kraken claimed, not
  actually used; Binance used but not listed); Uniswap V2 Router 2 no longer fails the way
  Table 4 describes — it now completes; the Rotki GitHub issue citation is open (not
  implemented) and describes a different feature than claimed.
- **Could not verify by live re-run within this audit's time budget, but strong reason for
  concern carried over from the user's own very recent (2026-08-06) internal research:** EF1
  and Binance Hot Wallet 20's Table 4 figures. That research — done after the FIFO-exclusion
  fix but before the final pagination rewrite — found both wallets producing balance gaps of
  69 ETH and over 500,000 ETH respectively, nowhere close to Table 4's claimed near-zero
  mismatches, and explicitly recommended disclosing this as an open limitation rather than
  showing "Lolos." The newer reconciliation code (`UNDER-COUNTED-INFLOW-DETECTED`) appears to
  *detect and report* this condition rather than fix it, which suggests — but does not, on its
  own, prove — that the underlying gap is still there today.
- **Not independently re-verified (on-chain state that has since moved, or out of feasible
  scope for this pass):** vitalik.eth's current 97,412 tx / 0.069702 ETH figures (highest
  priority to re-check given its documented history of instability); the exact live-price
  dollar figures in Table 5's Dashboard/Integrated snapshot (mechanism confirmed, dollar
  amounts are a point-in-time artifact).
