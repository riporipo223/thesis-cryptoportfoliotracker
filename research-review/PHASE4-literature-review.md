# Phase 4 — Literature Review Notes (Industry Tools + Academic Context)

Working document, not manuscript prose. Every source below is a real URL I retrieved via search this session or the prior session — none are invented. Where a claim could not be confirmed from a primary/official source, it is marked **[NEEDS MANUAL VERIFICATION]** rather than stated as fact. This document exists so you can decide which citations to actually add — it is the evidence trail, not the final reference list.

## Why this matters for the rejection

The reviewer's #1 stated reason was "novelty not sufficiently justified against existing tools." The current manuscript's related-work section (refs [3]–[8]) cites zero industry tools — only academic papers on adjacent topics (a price-tracking prototype, blockchain certificate storage, crowdfunding, e-voting, FIFO in accounting). That is the direct, fixable cause of this rejection reason, and this document is aimed squarely at fixing it.

## 1. Industry tools — verified capabilities, primary sources

### Koinly

| Claim | Source | Status |
|---|---|---|
| Paste a public wallet address, Koinly auto-syncs on-chain activity including gas fees and internal transfers, and excludes internal (wallet-to-own-wallet) transfers from taxable events | [Koinly — Settings: Wallet-based cost tracking](https://support.koinly.io/en/articles/9489991-settings-wallet-based-cost-tracking) | ✅ Primary source (official help center) |
| Supports FIFO, LIFO, and HIFO cost-basis methods | [Koinly — How to calculate cost basis](https://koinly.io/blog/calculate-cost-basis-crypto-bitcoin/) | ✅ Primary source |
| Fee value is added to the cost basis of the received asset; a fee paid in crypto is treated as a disposal (taxable event) of that crypto | [Koinly — Trading & transaction fees](https://support.koinly.io/en/articles/9490025-trading-fees-transaction-fees) | ✅ Primary source |

### Rotki (free, open-source — closest comparator)

| Claim | Source | Status |
|---|---|---|
| Supports FIFO, LIFO, HIFO, and ACB cost-basis methods, configurable per report | [rotki Docs — Customization/Settings](https://docs.rotki.com/usage-guides/customization.html) | ✅ Primary source (official docs) |
| Cost basis is calculated for all supported trades/on-chain events; PnL reports break down gains by event type (trades, fees, staking, airdrops) | [rotki Docs — Creating a profit/loss report](https://docs.rotki.com/usage-guides/history/pnl) | ✅ Primary source |
| "Wallet-based cost tracking" (i.e. deriving cost basis directly from on-chain wallet history rather than manually entered trades) was explicitly built as a named feature | [rotki GitHub Issue #2438 — "Add new accounting method: wallet-based cost tracking"](https://github.com/rotki/rotki/issues/2438) | ✅ Primary source — **this is the single strongest piece of evidence that the exact feature category claimed as novel already has a name and a shipped implementation in an open-source competitor** |
| Blockchain coverage: Ethereum + L2s, Bitcoin, Solana, Polkadot, Kusama, via user's own RPC/node | [rotki official site](https://rotki.com/) | ✅ Primary source |
| An accounting-rules setting lets users mark whether EVM gas cost counts as a realized loss | Search-summarized from rotki review coverage; **[NEEDS MANUAL VERIFICATION against rotki docs directly before citing as a specific claim]** | ⚠️ Secondary source only |

**Recommendation: cite Rotki as the primary related-work comparator, not Koinly.** It's free and open-source like this thesis's positioning, and issue #2438 is a citable, dated, verifiable primary source showing the "novel" feature was proposed and built as an open GitHub issue — the opposite of an invented claim.

### CoinTracker

| Claim | Source | Status |
|---|---|---|
| Cost basis method (FIFO/HIFO/Specific ID) is user-configurable; as of Jan 1, 2025 FIFO and Specific Identification (which includes HIFO/LIFO) are the only IRS-accepted methods for US digital-asset reporting | [CoinTracker — Cost basis methods for US customers](https://support.cointracker.io/hc/en-us/articles/4413071356177-Cost-basis-methods-for-US-customers) | ✅ Primary source — **also independently useful: shows FIFO is not just a design choice but increasingly a regulatory default in at least one major jurisdiction, which is a legitimate justification for FIFO-only scope this thesis can cite instead of just "easier to audit"** |
| Fee paid to acquire an asset is included in cost basis; fee paid in crypto is treated as a disposal | [CoinTracker — How transaction fees impact your tax calculations](https://support.cointracker.io/hc/en-us/articles/12029908614289-How-transaction-fees-impact-your-tax-calculations) | ✅ Primary source |

### CoinLedger

| Claim | Source | Status |
|---|---|---|
| Cost basis = purchase price + acquisition fees; sale-side fees reduce proceeds | [CoinLedger — How is cost basis calculated?](https://help.coinledger.io/en/articles/6145354-how-is-cost-basis-calculated) | ✅ Primary source |
| IRS has not given clear guidance on wallet-to-wallet transfer gas fees; such fees are usually not deductible unless directly tied to an acquisition/disposal | [CoinLedger — How to report crypto gas fees on taxes](https://coinledger.io/blog/ethereum-gas-fees) | ✅ Primary source — **useful nuance**: this is a real, citable regulatory ambiguity around exactly the gas-fee-reconciliation problem this thesis addresses. Worth a sentence in Discussion: existing commercial tools face the same ambiguity this thesis's gas-drain design resolves procedurally (deduct from FIFO balance) without claiming a tax position. |

### DeBank / Zapper / Zerion — view-only DeFi dashboards (closest UX comparators, not cost-basis comparators)

| Claim | Source | Status |
|---|---|---|
| DeBank: 50+ chains, view-only, no wallet-connect required for viewing, no confirmed cost-basis/tax feature | [DeFi Portfolio Tracker 2026: 6 Best Tools Compared](https://blog.portals.fi/defi-portfolio-tracker-comparison/) | ⚠️ Secondary source (comparison blog, not DeBank's own docs) — **[NEEDS MANUAL VERIFICATION on debank.com directly before citing "no cost basis feature" as a firm claim]** |
| Zerion: logs NFT acquisition cost, sale price, and holding period for tax purposes (NFT-specific; fungible-token cost-basis behavior not confirmed) | Search-summarized, no single authoritative Zerion doc page found | ⚠️ **[NEEDS MANUAL VERIFICATION]** — do not cite the "no cost basis" framing for Zerion specifically without checking zerion.io's own docs, since this one search result suggests partial tax-adjacent functionality exists |
| Zapper is winding down — site, apps, and API going offline Aug 3, 2026 | Referenced in the same comparison blog | ⚠️ Time-sensitive; if the paper cites Zapper as an active comparator, note its shutdown or drop it from the comparison table entirely |

**Recommendation:** keep DeBank/Zerion in the related-work table as "view-only dashboard" category with appropriate hedging language ("do not appear to offer," not "do not offer"), and do not cite Zapper as a live product given its shutdown.

## 2. Academic literature

Searched specifically for peer-reviewed work matching this thesis's exact niche (automated on-chain FIFO cost-basis reconstruction with gas-fee-aware balance reconciliation). **No paper matching that specific combination was found.** This is a real, narrower, and more defensible research gap than "no such system exists" — the gap is in the *academic* literature, not the *product* landscape, and that distinction should be made explicit rather than conflated.

| Source | Relevance | Status |
|---|---|---|
| [Blockchain Data Analytics: A Scoping Literature Review and Directions for Future Research](https://arxiv.org/abs/2505.04403) (arXiv, 2025) | Scoping review of 466 publications 2011–early 2024 on blockchain data analytics broadly. Directly useful as evidence that even a systematic review of the field's academic literature doesn't surface this thesis's specific niche — **but I have only read the abstract/search snippet, not the full text.** Before citing "this gap is confirmed by [X]," the authors should read the full paper and confirm it doesn't already cover wallet-based cost-basis reconstruction under a different name. | ⚠️ **[NEEDS FULL-TEXT VERIFICATION]** |
| [Portfolio Optimization Methods for the Digital Asset Market: A Comprehensive Survey](https://dl.acm.org/doi/10.1145/3819577) (ACM Computing Surveys, 2025) | Different scope — asset-allocation optimization, not cost-basis/tax accounting. Useful only as evidence the "portfolio management" academic literature exists and is active, not as a direct comparator. Do not cite this as covering the same problem — it doesn't. | ✅ Confirmed real (ACM CSUR, has a DOI), scope-mismatch noted so it isn't misused |
| Existing refs [7] (accounting FIFO), [3]–[6] (price-tracking prototype, blockchain certificates, crowdfunding, e-voting) already in the manuscript | Keep — these establish FIFO's accounting pedigree and blockchain-web integration feasibility, which are still legitimate supporting citations. They just aren't a substitute for citing the industry tools above. | Already verified in original manuscript |

## What I did NOT do

- Did not attempt to access rotki's or Koinly's actual source code/API to verify implementation details beyond what their own public docs state — this is a literature/documentation review, not a second code audit.
- Did not read the full text of the arXiv scoping review — flagged above as needing that follow-up before the manuscript leans on it for the novelty argument.
- Did not search exhaustively across all possible venues (SINTA-indexed Indonesian journals, non-English-language prior work on this exact topic) — if there's Indonesian-language prior art specifically (plausible, given JIKO's own audience), that's a gap this pass didn't cover and is worth a dedicated search before final submission.
