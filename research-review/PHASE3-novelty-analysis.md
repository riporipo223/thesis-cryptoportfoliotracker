# Phase 3 — Research Gap / Novelty Analysis

**Scope, as agreed:** feature comparison based on current public documentation of each product, not live account testing (no accounts were created). Every claim below is sourced from a live web search — see citations — not from training-data recall alone, since recall risked being stale for a fast-moving product category.

## The paper's novelty claim, verbatim (§1, translated)

> "The novelty of this research lies in integrating three aspects simultaneously: unifying manual and on-chain portfolio data sources, automating FIFO cost-basis calculation based on blockchain transaction reconstruction, and handling gas fees in balance reconciliation against the actual on-chain balance... No system has yet been found that automatically reconstructs on-chain transaction history to calculate cost basis using the FIFO method while also accounting for gas fee components in balance reconciliation."

## Verdict: this claim does not hold against current commercial tools

| Capability claimed as novel | Koinly | Rotki | CoinTracker | CoinLedger |
|---|---|---|---|---|
| Paste a public address, auto-sync on-chain history (no wallet-connect) | ✅ — "paste your public address and let Koinly sync on-chain activity" | ✅ — supports Ethereum/L2s, Bitcoin, Solana, Polkadot, Kusama via RPC/own node | ✅ | ✅ — reported as best-in-class at pulling on-chain data |
| Automated FIFO cost basis | ✅ (+ LIFO, HIFO) | ✅ (+ LIFO, HIFO, ACB) | ✅ (+ HIFO, others) | ✅ (+ LIFO, HIFO, Adjusted Cost) |
| Gas fee accounted in cost basis / reconciliation | ✅ — fee value added to cost basis of received asset; fee-in-crypto treated as a disposal event | ✅ — explicit setting for whether EVM gas cost counts as a loss | ✅ — fee included in cost basis, treated as disposal | ✅ — reported strongest specifically on gas/protocol-fee ingestion |
| Internal-transfer detection (exclude wallet-to-own-wallet) | ✅ — explicitly identifies and excludes internal transfers | not confirmed in this pass | not confirmed in this pass | not confirmed in this pass |
| DeFi protocol decoding | not confirmed | ✅ — Aave, Uniswap, Compound, Curve, Lido | not confirmed | not confirmed |

Sources: [Koinly cost basis](https://koinly.io/blog/calculate-cost-basis-crypto-bitcoin/), [Koinly wallet-based cost tracking](https://support.koinly.io/en/articles/9489991-settings-wallet-based-cost-tracking), [Koinly trading/transaction fees](https://support.koinly.io/en/articles/9490025-trading-fees-transaction-fees), [Rotki official site](https://rotki.com/), [Rotki review 2026](https://cryptoadventure.com/rotki-review-2026-privacy-first-local-portfolio-tracking-and-crypto-accounting/), [CoinTracker fee handling](https://support.cointracker.io/hc/en-us/articles/12029908614289-How-transaction-fees-impact-your-tax-calculations), [CoinLedger cost basis](https://help.coinledger.io/en/articles/6145354-how-is-cost-basis-calculated), [Koinly vs CoinTracker comparison](https://coinledger.io/tools/koinly-vs-cointracker).

**All three components of the claimed novelty — (a) automated on-chain reconstruction, (b) FIFO cost basis, (c) gas-fee-aware reconciliation — already exist, in combination, in production, in at least four widely-used tools, one of which (Rotki) is free and open-source.** This is not a matter of interpretation; it's directly documented in each product's own help center. A reviewer with even shallow familiarity with the crypto-tax-software space (a near-certainty for anyone reviewing a paper on this exact topic) will very likely raise this.

Compounding the problem: the paper's related-work section (§1, refs [3]-[7]) cites only academic papers — a crypto price-tracking prototype, a blockchain certificate-storage system, a crowdfunding platform, an e-voting system, and an accounting-FIFO paper. **None of the existing commercial crypto-tax/portfolio tools are cited or discussed anywhere in the paper.** For a thesis whose central contribution is explicitly a *system*, not an algorithm, omitting the dominant existing systems in that exact space is a real research-gap-analysis failure, not just a novelty overclaim.

## What legitimately differs (a narrower, defensible novelty)

The system isn't without a real niche — it's just a narrower one than claimed:

1. **Free, self-hosted-style, no-signup, no-subscription.** Koinly/CoinTracker/CoinLedger are commercial SaaS with paid tiers gating cost-basis reports. Rotki is the closest comparator (free, open-source, similar read-only philosophy) — the paper should engage with Rotki directly as its nearest neighbor rather than not mentioning it.
2. **Deliberately narrow scope as a design choice, not a limitation to apologize for.** Where Koinly/CoinTracker/CoinLedger are full multi-exchange, multi-chain tax-report generators (dozens of integrations, jurisdiction-specific tax forms), and DeBank/Zapper/Zerion are view-only balance dashboards with **no cost-basis feature at all**, this system sits in a real but underserved middle: manual entries + a couple of chains + auditable cost basis, without needing exchange API keys, CSV imports, or a subscription. That's a legitimate positioning, but it should be argued as "a lightweight, transparent alternative to X and Y for a narrower use case," not "no such system exists."
3. **Pedagogical/replication value.** As a undergraduate thesis demonstrating a working, auditable, reproducible cost-basis pipeline end-to-end (including the honest failure modes this review's benchmark surfaced), it has real value as a *learning artifact and open reference implementation* — a framing the paper doesn't currently use but which is more defensible than a novelty claim that a five-minute search disproves.

## DeBank / Zapper / Zerion / CoinStats — the "view-only dashboard" category

These are the closest cousins to this app's read-only, address-based UX (no wallet-connect, no private key) — but they occupy a different job: real-time balance/yield/DeFi-position visualization, not cost basis or P&L. Search results found no evidence of FIFO/cost-basis features in any of them; they are explicitly not tax/accounting tools. Note: Zapper is winding down (shutting off Aug 3, 2026 per its own announcement), which is incidental but worth knowing if the paper cites it as an active comparator later. [Source](https://blog.portals.fi/defi-portfolio-tracker-comparison/).

## Recommendation for the paper

Rewrite the novelty paragraph (§1) to:
1. Explicitly name and cite Koinly, Rotki, CoinTracker, CoinLedger, DeBank/Zapper/Zerion as related work (industry, not just academic).
2. Drop the "no such system exists" framing.
3. Reposition the contribution around the narrower, real differentiators above: free/no-signup, unifies manual+on-chain without exchange integrations, and — most defensibly — the auditability trail down to source transaction, once the WAC-fallback fix from Phase 1/2 is in place. That last point is worth leaning into precisely because Rotki/Koinly are closed/commercial black boxes for the reconciliation step; this system's is inspectable in a way a thesis reviewer can actually verify, which is a genuinely different claim than "first to do X."
