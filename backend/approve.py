"""The human approval step.

This is deliberately NOT an MCP tool. If approving were a tool, an agent could
call it and approve its own payment, which is exactly what the shop rule
forbids. Approval lives here instead, as something a person runs.

Usage, from the Homework 5 folder:

    .venv/Scripts/python.exe -m backend.approve --list
    .venv/Scripts/python.exe -m backend.approve --approve APR-1234ABCD --by "Purnima Prasad"
    .venv/Scripts/python.exe -m backend.approve --reject APR-1234ABCD --by "Purnima Prasad" --note "too tight this month"
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

from .config import OUTPUT_DIR, PROJECT_ROOT

APPROVALS_PATH = OUTPUT_DIR / "approvals.json"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"


def _load() -> list[dict]:
    if not APPROVALS_PATH.exists():
        return []
    raw = json.loads(APPROVALS_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else [raw]


def _save(records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Rename into place: a plain write truncates first, so a crash mid-write
    # would leave invalid JSON where the signed decisions used to be.
    tmp = APPROVALS_PATH.with_name(APPROVALS_PATH.name + '.writing')
    tmp.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, APPROVALS_PATH)


def _shop_date() -> str:
    conn = sqlite3.connect(f"file:{WORKING_DB}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()[0]
    finally:
        conn.close()


def _balance() -> float:
    conn = sqlite3.connect(f"file:{WORKING_DB}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT balance FROM cash_accounts WHERE name='checking'"
        ).fetchone()[0]
    finally:
        conn.close()


def _is_payment(record: dict) -> bool:
    """A payment moves cash. A price override only agrees what to charge."""
    return record.get("category", "payment") == "payment"


def _one_line(record: dict) -> str:
    """One readable line for either shape of request."""
    if _is_payment(record):
        return (f"{record['kind']} #{record['ref_id']}  "
                f"${record['amount']:,.2f}  from {record['account']}")
    return (f"{record['kind']} ticket #{record.get('ticket_id', record.get('ref_id'))}  "
            f"{record.get('qty')} x {record.get('sku')} {record.get('size')} at "
            f"${record.get('proposed_unit_price', 0):,.2f}/unit  "
            f"(list ${record.get('list_price', 0):,.2f}, cost ${record.get('unit_cost', 0):,.2f})")


def show() -> None:
    records = _load()
    if not records:
        print("No approval requests on the board.")
        return
    balance = _balance()
    print(f"checking balance: ${balance:,.2f}   shop date: {_shop_date()}\n")
    for r in records:
        mark = {"pending": "[ ]", "approved": "[x]", "rejected": "[-]"}.get(r["status"], "[?]")
        print(f"{mark} {r['approval_id']}  {r['status']:9} {_one_line(r)}")
        print(f"      asked by : {r['requested_by']} on shop date {r['requested_on_shop_date']}")
        print(f"      reason   : {r['reason']}")
        if r["status"] == "pending" and _is_payment(r):
            after = balance - r["amount"]
            verdict = f"would leave ${after:,.2f}" if after >= 0 else \
                      f"WOULD OVERDRAW by ${abs(after):,.2f} — the pay tool will refuse this"
            print(f"      if paid  : {verdict}")
        elif r["status"] == "pending":
            print(f"      if agreed: moves no cash — agreeing a price is not a purchase")
        if r.get("approved_by"):
            print(f"      decided  : {r['status']} by {r['approved_by']} on {r['decided_on']}")
        if r.get("consumed_by_payment_id"):
            print(f"      used for : payment #{r['consumed_by_payment_id']}")
        print()


def decide(approval_id: str, status: str, by: str, note: str | None) -> int:
    records = _load()
    for r in records:
        if r["approval_id"] != approval_id:
            continue
        if r["status"] != "pending":
            print(f"{approval_id} is already '{r['status']}'. Not changing it.")
            return 1
        r["status"] = status
        r["approved_by"] = by if status == "approved" else None
        r["decided_on"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        r["decision_note"] = note
        _save(records)
        print(f"{approval_id} -> {status} by {by}")
        if status == "approved" and _is_payment(r):
            after = _balance() - r["amount"]
            print(f"  ${r['amount']:,.2f} cleared to pay; would leave ${after:,.2f}")
            if after < 0:
                print("  note: this still cannot be paid — the pay tool refuses overdrafts.")
        elif status == "approved":
            print(f"  ${r.get('proposed_unit_price', 0):,.2f}/unit agreed. No cash moves.")
        print("  recorded on the board only. The dashboard is what writes the decision "
              "into the ticket and runs the payment.")
        return 0
    print(f"No approval request with id {approval_id}.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Human approval for Campus Customs payments.")
    parser.add_argument("--list", action="store_true", help="Show the approval board.")
    parser.add_argument("--approve", metavar="APPROVAL_ID")
    parser.add_argument("--reject", metavar="APPROVAL_ID")
    parser.add_argument("--by", default="", help="Name of the person deciding.")
    parser.add_argument("--note", default=None, help="Optional reason for the decision.")
    args = parser.parse_args()

    if args.approve or args.reject:
        if not args.by.strip():
            print("--by is required: a decision must name the person who made it.")
            return 1
        if args.approve:
            return decide(args.approve, "approved", args.by, args.note)
        return decide(args.reject, "rejected", args.by, args.note)

    show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
