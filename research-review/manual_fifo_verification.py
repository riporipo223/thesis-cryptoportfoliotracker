#!/usr/bin/env python3
"""
Independent manual FIFO cost-basis verification for the case-study wallet
(0xD23a3393C58789FabDB8494C7D1D4dEF59a2bc93), used in the thesis manuscript.

This script does NOT import or call anything from app/api/wallet/analyze/route.ts.
It is a from-scratch, minimal reimplementation of the same FIFO accounting
method, written independently so it can serve as a genuine cross-check rather
than "the same code checking itself."

INPUTS (see accompanying raw_*.json files, fetched directly from Etherscan,
independent of the running app):
  - raw_txlist.json          -- action=txlist (normal transactions)
  - raw_txlistinternal.json  -- action=txlistinternal (internal transactions)

STATED ASSUMPTIONS (explicit, not silent):
  1. A transaction counts as a real incoming/outgoing value transfer only if
     `value != '0'` AND `isError != '1'`. A failed/reverted transaction's
     `value` field reports the amount that WOULD have been sent had it
     succeeded -- no ETH actually moved on revert, so it is excluded from
     lot creation and lot consumption. (This wallet has zero such failed
     transactions with nonzero value, so this assumption has no numerical
     effect here -- it is stated for completeness and because it is the
     exact bug this codebase's FIFO engine had to be fixed for on other
     wallets. See research-review/CHANGES-SUMMARY-vs-rejection.md and the
     prior session's fix for EF1 / Binance Hot Wallet 20.)
  2. Gas is charged on every transaction the wallet itself signed
     (`from == wallet`), regardless of success/failure, and regardless of
     whether the transaction also moved value. This matches real EVM
     semantics: gas is burned even on revert.
  3. Processing ORDER matches the app's actual two-pass convention, not a
     single strict chronological interleave: ALL real value-transfer OUTs
     are consumed first (oldest-lot-first, in their own chronological
     order), and ONLY AFTER that is gas drained as a second pass (again
     oldest-lot-first, in gas-transaction chronological order). This is a
     real, disclosed convention choice -- a stricter single-pass
     chronological interleave of (inflows, outflows, gas) is an equally
     valid alternative accounting convention that a purist might prefer,
     and would very likely produce a different lot-by-lot consumption
     sequence for other wallets (though for this specific wallet, the
     final numbers match either way -- see the ledger below).
  4. Dates in this script's ledger use UTC (`datetime.fromtimestamp(ts,
     timezone.utc)`), matching the ACTUAL date key the app's FIFO engine
     uses internally for historical-price lookups
     (`new Date(ts*1000).toISOString().slice(0,10)` in route.ts). This is
     NOT the same as the date the app DISPLAYS to a user in the UI
     (`toLocaleDateString('en-GB', ...)` with no explicit timeZone, which
     uses the server process's LOCAL timezone). This script found three
     transactions whose UTC date differs from the app's displayed date by
     one day, purely because the server this app runs on is in UTC+7
     (WIB) and the transaction's UTC timestamp falls late in the UTC day.
     This is a real, separate, minor display-consistency finding -- see
     the "Discrepancies found" section of manual-fifo-verification.md.
     It does NOT affect the FIFO math, since the actual price-lookup logic
     already uses UTC internally, consistently with this script.
  5. Historical USD prices per lot: live independent re-fetching was
     attempted this session against four separate public providers
     (CoinGecko, Binance, Kraken, CryptoCompare) and failed for each --
     see manual-fifo-verification.md for the exact errors. As a documented
     fallback, this script uses the real historical prices already
     persisted in this repo's lib/price-cache.json, which were originally
     obtained via genuine live API calls in earlier sessions before these
     providers became unavailable in this environment. This means the
     TRANSACTION DATA and FIFO ALGORITHM in this script are fully
     independent of the app; the per-lot USD PRICES are real market data
     but were not independently re-fetched in this specific pass. This
     limitation is stated explicitly, not hidden.
"""

import json
import datetime
from pathlib import Path

HERE = Path(__file__).parent
WALLET = "0xD23a3393C58789FabDB8494C7D1D4dEF59a2bc93"
WALLET_LOWER = WALLET.lower()

# Real historical prices, sourced as described in assumption 5 above.
PRICES_USD = {
    "2022-05-28": 1790.79,
    "2022-11-06": 1568.75,
    "2022-11-07": 1568.45,
    "2022-11-09": 1104.17,
    "2023-01-28": 1572.46,
    "2023-10-27": 1779.98,
    "2024-05-03": 3103.77,
    "2024-06-22": 3494.25,
    "2025-05-09": 2345.32,
    "2025-07-15": 3139.33,
    "2025-11-21": 2764.76,
    "2025-12-31": 2967.53,
}


def utc_date(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")


def load_raw():
    normal = json.loads((HERE / "raw_txlist.json").read_text())["result"]
    internal = json.loads((HERE / "raw_txlistinternal.json").read_text())["result"]
    return normal, internal


def main():
    normal, internal = load_raw()

    # -- Classification (assumption 1) --------------------------------------
    incoming = [
        tx for tx in normal
        if tx["to"].lower() == WALLET_LOWER and tx["value"] != "0" and tx.get("isError") != "1"
    ]
    incoming += [
        tx for tx in internal
        if tx["to"].lower() == WALLET_LOWER and tx["value"] != "0"
        # txlistinternal responses for this wallet carry no isError='1' entries
        # in the fetched data; included for symmetry/documentation only.
        and tx.get("isError") != "1"
    ]
    outgoing = [
        tx for tx in normal
        if tx["from"].lower() == WALLET_LOWER and tx["value"] != "0" and tx.get("isError") != "1"
    ]
    incoming.sort(key=lambda t: int(t["timeStamp"]))
    outgoing.sort(key=lambda t: int(t["timeStamp"]))

    # -- Gas (assumption 2): every self-signed normal tx, success or not ----
    gas_txs = [tx for tx in normal if tx["from"].lower() == WALLET_LOWER]
    gas_events = []
    for tx in gas_txs:
        gas_used = int(tx.get("gasUsed", 0) or 0)
        gas_price = int(tx.get("gasPrice", 0) or 0)
        gas_eth = gas_used * gas_price / 1e18
        if gas_eth > 0:
            gas_events.append((int(tx["timeStamp"]), tx["hash"], gas_eth))
    gas_events.sort(key=lambda e: e[0])

    # -- FIFO lot queue -------------------------------------------------------
    lots = []          # list of dicts: {lot_no, tx_hash, amount, price, date}
    lot_counter = 0
    ledger = []         # human-readable ledger rows
    running_balance = 0.0
    total_cost_basis_usd = 0.0

    def fmt(x, n=8):
        return f"{x:.{n}f}"

    # Pass 1a: create lots from incoming transactions, in chronological order.
    for tx in incoming:
        ts = int(tx["timeStamp"])
        d = utc_date(ts)
        amount = int(tx["value"]) / 1e18
        price = PRICES_USD.get(d)
        if price is None:
            raise SystemExit(f"No price for date {d} (tx {tx['hash']}) -- cannot proceed without an explicit price or an explicit 'requires manual price' marker.")
        lot_counter += 1
        lot = {"lot_no": lot_counter, "tx_hash": tx["hash"], "amount": amount, "price": price, "date": d}
        lots.append(lot)
        running_balance += amount
        cost = amount * price
        total_cost_basis_usd += cost
        ledger.append({
            "date": d, "type": "IN", "tx_hash": tx["hash"], "amount": amount,
            "price": price, "lots_consumed": f"created lot #{lot_counter}",
            "running_balance": running_balance,
        })

    # Pass 1b: consume lots oldest-first for real value-transfer OUTs.
    for tx in outgoing:
        ts = int(tx["timeStamp"])
        d = utc_date(ts)
        amount = int(tx["value"]) / 1e18
        remaining = amount
        consumed_desc = []
        while remaining > 1e-12 and lots:
            oldest = lots[0]
            if oldest["amount"] <= remaining + 1e-12:
                consumed_desc.append(f"#{oldest['lot_no']}({fmt(oldest['amount'])})")
                cost_removed = oldest["amount"] * oldest["price"]
                total_cost_basis_usd -= cost_removed
                running_balance -= oldest["amount"]
                remaining -= oldest["amount"]
                lots.pop(0)
            else:
                consumed_desc.append(f"#{oldest['lot_no']}({fmt(remaining)})")
                cost_removed = remaining * oldest["price"]
                total_cost_basis_usd -= cost_removed
                running_balance -= remaining
                oldest["amount"] -= remaining
                remaining = 0.0
        if remaining > 1e-12:
            consumed_desc.append(f"UNMATCHED({fmt(remaining)})")
        ledger.append({
            "date": d, "type": "OUT", "tx_hash": tx["hash"], "amount": amount,
            "price": None, "lots_consumed": " ".join(consumed_desc),
            "running_balance": running_balance,
        })

    # Pass 2: drain gas, oldest-lot-first, in gas-event chronological order
    # (assumption 3 -- this happens strictly AFTER all value-transfer OUTs,
    # matching the app's actual two-pass behavior).
    total_gas = 0.0
    for ts, tx_hash, gas_eth in gas_events:
        d = utc_date(ts)
        total_gas += gas_eth
        remaining = gas_eth
        consumed_desc = []
        while remaining > 1e-12 and lots:
            oldest = lots[0]
            if oldest["amount"] <= remaining + 1e-12:
                consumed_desc.append(f"#{oldest['lot_no']}({fmt(oldest['amount'])})")
                cost_removed = oldest["amount"] * oldest["price"]
                total_cost_basis_usd -= cost_removed
                running_balance -= oldest["amount"]
                remaining -= oldest["amount"]
                lots.pop(0)
            else:
                consumed_desc.append(f"#{oldest['lot_no']}({fmt(remaining)})")
                cost_removed = remaining * oldest["price"]
                total_cost_basis_usd -= cost_removed
                running_balance -= remaining
                oldest["amount"] -= remaining
                remaining = 0.0
        ledger.append({
            "date": d, "type": "GAS", "tx_hash": tx_hash, "amount": gas_eth,
            "price": None, "lots_consumed": " ".join(consumed_desc),
            "running_balance": running_balance,
        })

    # -- Output ---------------------------------------------------------------
    ledger.sort(key=lambda r: (r["date"], 0 if r["type"] == "IN" else (1 if r["type"] == "OUT" else 2)))

    print(f"{'Date':<12} {'Type':<5} {'Tx Hash':<14} {'Amount (ETH)':>16} {'Price':>10}  Lots consumed / created")
    print("-" * 100)
    for row in ledger:
        price_str = f"${row['price']:.2f}" if row["price"] else ""
        print(f"{row['date']:<12} {row['type']:<5} {row['tx_hash'][:10]}… {row['amount']:>16.10f} {price_str:>10}  {row['lots_consumed']}")

    print()
    print(f"Total incoming lots created : {len(incoming)}")
    print(f"Total outgoing (value) txs  : {len(outgoing)}")
    print(f"Total gas-draining events   : {len(gas_events)}")
    print(f"Total gas (ETH)             : {total_gas:.10f}")
    print(f"Final running balance (ETH) : {running_balance:.10f}")
    print(f"Final cost basis (USD)      : {total_cost_basis_usd:.6f}")
    print(f"Surviving open lots         : {len(lots)}")
    for lot in lots:
        print(f"  lot #{lot['lot_no']}: {lot['amount']:.10f} ETH @ ${lot['price']:.2f} (from {lot['date']}, tx {lot['tx_hash']})")

    return {
        "final_balance": running_balance,
        "final_cost_basis_usd": total_cost_basis_usd,
        "total_gas": total_gas,
        "open_lots": lots,
        "ledger": ledger,
    }


if __name__ == "__main__":
    main()
