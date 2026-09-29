# Independent Manual FIFO Verification — Case-Study Wallet

Addresses the manuscript rejection reason "no benchmark against existing applications or manual calculations" — specifically the *manual calculation* half (the *existing applications* half is covered separately as a feature comparison, not a numeric benchmark, per an earlier scoping decision — see `PHASE3-novelty-analysis.md`).

**Wallet:** `0xD23a3393C58789FabDB8494C7D1D4dEF59a2bc93` (the manuscript's own primary case-study wallet)

## What "independent" means here, precisely

| Component | Independent? | How |
|---|---|---|
| Transaction data | ✅ Fully independent | Fetched directly from Etherscan (`raw_txlist.json`, `raw_txlistinternal.json`, both saved alongside this report) — not derived from or copied out of the app's API response. |
| FIFO algorithm | ✅ Fully independent | `manual_fifo_verification.py` is a from-scratch ~200-line script. It does not import, call, or copy logic from `app/api/wallet/analyze/route.ts`. Written by re-deriving the FIFO method from the manuscript's own description (§2.4), not by reading the app's implementation and transcribing it. |
| Balance reconciliation | ✅ Fully independent | Computed purely from the transaction data + FIFO logic above; does not use the app's `balanceMismatch` field at all. |
| Historical USD prices | ⚠️ Partially independent — disclosed, not hidden | Four independent live re-fetch attempts were made this session (CoinGecko, Binance, Kraken, CryptoCompare) and **all four failed** for verifiable reasons (below). As a documented fallback, this script uses the real historical prices already persisted in `lib/price-cache.json` — genuine market data obtained via live API calls in earlier sessions, not fabricated, but not independently *re-fetched* in this specific pass. See "Price-fetching attempts" below for the exact errors. |

This distinction matters for how the manuscript should describe this check: it is an independent verification of the **FIFO accounting logic and balance reconciliation**, using **real but not freshly-independently-sourced** historical prices for the USD figures specifically.

## Price-fetching attempts (all failed, for real, verifiable reasons)

| Provider | Result |
|---|---|
| CoinGecko `/coins/ethereum/history` | `HTTP 401 Unauthorized` on 7 of 12 dates, `HTTP 429 Too Many Requests` on the remaining 5 — CoinGecko now requires an API key for this endpoint even on free tier, consistent with issues already flagged in prior sessions. |
| Binance `/api/v3/klines` | `SSL: CERTIFICATE_VERIFY_FAILED — Hostname mismatch` on every call — TLS-level interception in this sandbox environment, consistent with the "[Binance] skip: timeout/blocked" pattern already observed and flagged in the app's own server logs in prior sessions. |
| Kraken `/0/public/OHLC` | Same TLS certificate mismatch as Binance. |
| CryptoCompare `/data/pricehistorical` | `HTTP 401 Unauthorized` — matches the exact failure mode already found and documented for this provider in the prior session's benchmark work. |

None of these are new discoveries — they corroborate findings already on record from earlier sessions (`PHASE6-8-benchmark-report-v2-fixes.md`). What's new here is confirming the *same* restrictions apply even to a script with zero connection to the running app, ruling out "something about the app's fetch setup" as the cause — this is an environment/provider-level restriction, not an app bug.

## Stated assumptions (explicit, not silent)

1. A transaction counts as a real value transfer only if `value != '0'` **and** `isError != '1'`. This wallet has **zero failed transactions with nonzero value** (confirmed by direct inspection of the raw data), so this assumption has no numerical effect here — it's stated because it's the exact rule the app's FIFO engine needed fixing for on other wallets (EF1, Binance Hot Wallet 20 — see prior session).
2. Gas is charged on every self-signed transaction regardless of success or whether it also moved value — real EVM behavior.
3. **Processing order matches the app's actual two-pass convention**: all real value-transfer OUTs are consumed first (oldest-lot-first), and gas is drained in a *separate second pass* afterward — not a single chronologically-interleaved pass. This is a deliberate, disclosed choice to make an apples-to-apples comparison against the app's actual behavior; a stricter single-pass chronological interleave of inflows/outflows/gas is an equally defensible alternative convention that could produce a different lot-by-lot consumption sequence on a different wallet (for this wallet, as shown below, the final numbers match either way, but this is not guaranteed in general).
4. Dates use UTC, matching the app's actual internal price-lookup key — **not** the app's UI-displayed date, which uses the server's local timezone. See "Discrepancy found" below.

## Lot-by-lot ledger

Full ledger (105 rows: 12 IN, 7 OUT, 104 GAS spread across 86 distinct gas-only transactions — some transactions both transfer value and pay gas, counted once each per event type) is in `manual_fifo_verification.py`'s output; reproduce with `python3 manual_fifo_verification.py`. Abbreviated to the value-moving events (all 12 IN + 7 OUT rows, gas rows omitted for readability — full gas detail is in the script output and is a straightforward "which lot did this gas payment drain" trace any reviewer can rerun):

| Date (UTC) | Type | Tx Hash (short) | Amount (ETH) | Price | Lots created/consumed | Running balance (ETH) |
|---|---|---|---|---|---|---|
| 2022-05-28 | IN | 0xdad20822… | 0.01139556 | $1790.79 | created lot #1 | 0.01139556 |
| 2022-11-06 | IN | 0xc6107d46… | 0.00241812 | $1568.75 | created lot #2 | 0.01377147 (before gas) |
| 2022-11-07 | IN | 0xb92f6409… | 0.00240298 | $1568.45 | created lot #3 | +lot #3 |
| 2022-11-07 | OUT | 0x13a1db42… | 0.00120000 | — | #1(0.00120000) | −0.00120000 |
| 2022-11-09 | IN | 0xb3ef379c… | 0.00377398 | $1104.17 | created lot #4 | +lot #4 |
| 2022-11-09 | OUT | 0x97a2657d… | 0.00145000 | — | #1(0.00145000) | −0.00145000 |
| 2023-01-28 | IN | 0x37496e0b… | 0.00910000 | $1572.46 | created lot #5 | +lot #5 |
| 2023-03-08 | OUT | 0x3c190953… | 0.00300000 | — | #1(0.00300000) | −0.00300000 |
| 2023-10-27 | IN | 0x2c1cca40… | 0.00999763 | $1779.98 | created lot #6 | +lot #6 |
| 2024-04-25 | OUT | 0x3193103a… | 0.00330000 | — | #1(0.00330000) | −0.00330000 |
| 2024-05-03 | IN | 0xcb3084f0… | 0.00056000 | $3103.77 | created lot #7 | +lot #7 |
| 2024-06-22 | IN | 0xc94ccb4d… | 0.00261866 | $3494.25 | created lot #8 | +lot #8 |
| 2024-11-04 | OUT | 0xe80a25f8… | 0.00042049 | — | #1(0.00042049) — **lot #1 fully exhausted** | −0.00042049 |
| 2025-05-09 | IN | 0x281303da… | 0.04827406 | $2345.32 | created lot #9 | +lot #9 |
| 2025-07-08 | OUT | 0xe360bc66… | 0.02400000 | — | #1(0.00202507) #2(0.00241812) #3(0.00240298) #4(0.00377398) #5(0.00910000) #6(0.00427985) — spans 6 lots | −0.02400000 |
| 2025-07-15 | IN | 0xb4dc92fc… | 0.02400000 | $3139.33 | created lot #10 | +lot #10 |
| 2025-07-15 | OUT | 0x9d36c444… | 0.04535691 | — | #6(0.00571778) #7(0.00056000) #8(0.00261866) #9(0.03646047) — lots #6, #7, #8 fully exhausted | −0.04535691 |
| 2025-11-21 | IN | 0xdcd471d9… | 0.00016897 | $2764.76 | created lot #11 | +lot #11 |
| 2025-12-31 | IN | 0x9e8d4db9… | 0.01042946 | $2967.53 | created lot #12 | +lot #12 |

After all 12 IN, 7 OUT, and 104 gas-draining events (full gas trace in the script's stdout), lots #1 through #11 are fully consumed. **One lot survives: #12, 0.0082505802 ETH @ $2967.53, from tx `0x9e8d4db9…`, dated 2025-12-31.**

## Comparison: manual result vs. system result

Both computed against the same on-chain snapshot (system re-run immediately before this check; on-chain balance confirmed via `/api/wallet`: `0.008250580213914344 ETH`).

| Metric | Manual (independent) | System (`/api/wallet/analyze`) | Delta | Explained? |
|---|---|---|---|---|
| Final ETH balance | 0.0082505802 | 0.00825059 (displayed) / 0.008250580213914344 − 9.786085657104149e-09 internally | ~1.4×10⁻¹¹ ETH from true on-chain; system's own `balanceMismatch` is 9.79×10⁻⁹ ETH | ✅ Yes — see below |
| Final cost basis (USD) | $24.483844 | $24.483880966771558 | $0.000037 | ✅ Yes — see below |
| Surviving open lot | 1 lot: 0.0082505802 ETH @ $2967.53, tx `0x9e8d4db9…` | 1 lot: 0.0082506 ETH @ $2967.53, tx `0x9e8d4db9…` | Same transaction, same price, difference only in displayed decimal places | ✅ Match |
| Total gas drained | 0.0381614305 ETH | 0.038161 ETH (displayed, matches to shown precision) | negligible | ✅ Match |
| Incoming lots | 12 | 12 | 0 | ✅ Match |
| Outgoing (value) txs | 7 | 7 | 0 | ✅ Match |

**Both discrepancies (balance: ~1e-8 ETH scale; cost basis: ~$0.00004) are explained by a rounding-convention difference, not a logic error**: the app's engine calls `Number(x.toFixed(8))` after *every one* of its ~123 individual lot-consumption operations (each OUT and each GAS event), rounding the running ETH total to 8 decimal places at each step. This standalone script does not round intermediate values at all — only at final display. Over ~123 sequential floating-point operations, the two conventions accumulate slightly different rounding noise. Both are many orders of magnitude below the manuscript's own stated pass threshold (`< 10⁻⁶ ETH`, Table 2), and both are financially meaningless (the cost-basis delta is $0.000037, less than four-thousandths of a cent). **This is not a bug in either implementation — it's confirmation that two independently-written FIFO engines, given the same real transaction data, converge to the same answer within floating-point tolerance.**

## Other discrepancies found during this verification (disclosed per standing instructions, even though outside this task's core ask)

### 1. UI-displayed transaction dates use local server time, not UTC (3 of 19 transactions affected)

Systematically checked all 19 value-moving transactions: the app's `dateStr` field (shown in the UI and in `/logs/fifo-audit-*.txt`) disagreed with the transaction's true UTC calendar date in **3 cases** — `0xc6107d46…` (Nov 6 UTC, shown as "7 Nov 2022"), `0x2c1cca40…` (Oct 27 UTC, shown as "28 Oct 2023"), and `0xe360bc66…` (Jul 8 UTC, shown as "9 Jul 2025"). All three transactions occurred at or after 17:00:00 UTC — root cause confirmed: `route.ts` formats display dates with `date.toLocaleDateString('en-GB', {...})` with no explicit `timeZone`, which uses the Node process's local system timezone (this machine runs UTC+7 / WIB), while the app's actual FIFO price-lookup logic correctly keys off `date.toISOString().slice(0,10)` (UTC). **This does not affect the FIFO math or cost-basis accuracy** — the price actually used for each lot is looked up via the correct UTC date internally — it only affects the human-readable label shown to a user, which can read one calendar day later than the transaction's real UTC date. Cosmetic but genuinely confusing for anyone trying to cross-reference against Etherscan (which displays UTC by default). Not fixed here — code changes are out of this task's scope — flagged for a follow-up.

### 2. Transient Etherscan API errors are silently swallowed as "zero transactions," not surfaced as errors

While capturing the system's baseline output for this comparison, one `/api/wallet/analyze` call returned `transactions: 2` (instead of the expected, consistent 12) with no warning or error field set. Investigating the server log showed the root cause: `Fetched 0 ETH tx (1 page(s)), 2 internal tx (2 page(s))` — the normal `txlist` fetch got a non-`'1'` status from Etherscan (very likely a transient rate-limit response, plausible given how heavily this session alone has hit Etherscan's API) and the pagination function's error handling (`console.error(...); break;`) treats this the same as a legitimate empty result — it does not set `truncated: true`, does not surface an error to the API response, and does not retry. A second call moments later returned the correct, consistent result (12 transactions). **This is a real, reproducible-in-principle bug**: any transient upstream API error currently produces a silently-wrong low-transaction-count result indistinguishable from a genuinely quiet wallet, rather than an explicit error or truncation flag. Not fixed here — out of this task's scope (code changes excluded) — flagged for a follow-up fix (should not `break` silently on a non-`'1'`/non-"No transactions found" status; should set an explicit error/retry state instead).

## Suggested manuscript paragraph (validation section)

> Sebagai pemeriksaan independen atas mesin FIFO, dikembangkan skrip verifikasi terpisah (tidak menggunakan kode sistem) yang merekonstruksi cost basis dompet studi kasus dari data transaksi mentah yang diambil langsung dari Etherscan. Skrip ini menerapkan logika FIFO yang sama secara independen — antrean lot, konsumsi lot tertua terlebih dahulu, dan pengurangan biaya gas — dan menghasilkan buku besar (ledger) lot demi lot yang dapat ditelusuri secara manual terhadap Etherscan. Hasil rekonstruksi independen (saldo akhir 0,00825058 ETH, cost basis USD 24,48, satu lot tersisa dari transaksi tanggal 31 Desember 2025) sesuai dengan hasil sistem hingga orde 10⁻⁸ ETH dan USD 0,00004 — selisih yang sepenuhnya dijelaskan oleh perbedaan konvensi pembulatan antarlangkah, bukan kesalahan logika, dan berada jauh di bawah ambang batas validasi yang ditetapkan (< 10⁻⁶ ETH). Perlu dicatat bahwa harga historis USD per lot pada verifikasi ini menggunakan data harga yang telah tervalidasi dari sesi sebelumnya (empat percobaan pengambilan harga langsung dari penyedia publik pada sesi ini gagal karena pembatasan API/jaringan pada lingkungan pengujian), sehingga independensi verifikasi ini berlaku penuh pada data transaksi dan logika algoritma FIFO, namun tidak pada pengambilan-ulang harga historis secara langsung.

(Direct translation for internal review, not for the paper: "As an independent check on the FIFO engine, a separate verification script was developed — not using the system's code — that reconstructs the case-study wallet's cost basis from raw transaction data pulled directly from Etherscan. This script applies the same FIFO logic independently — lot queue, oldest-lot-first consumption, gas deduction — and produces a lot-by-lot ledger that can be manually traced against Etherscan. The independent reconstruction result (final balance 0.00825058 ETH, cost basis USD 24.48, one surviving lot from the 31 December 2025 transaction) matches the system's result to within 10⁻⁸ ETH and USD 0.00004 — a difference fully explained by a step-by-step rounding-convention difference, not a logic error, and far below the established validation threshold (< 10⁻⁶ ETH). Note that per-lot historical USD prices in this verification use price data already validated from earlier sessions (four attempts to fetch prices directly from public providers in this session failed due to API/network restrictions in the test environment), so this verification's independence applies fully to the transaction data and FIFO algorithm logic, but not to re-fetching historical prices directly.")

## Files produced

- [`manual_fifo_verification.py`](manual_fifo_verification.py) — the standalone script (run with `python3 manual_fifo_verification.py` from this directory; reproduces the full ledger including all 104 gas-drain rows).
- [`raw_txlist.json`](raw_txlist.json), [`raw_txlistinternal.json`](raw_txlistinternal.json) — raw Etherscan responses this script consumes, saved for reproducibility.
- This file.

Nothing in `route.ts`, `audit.ts`, or the manuscript was modified as part of this task.
