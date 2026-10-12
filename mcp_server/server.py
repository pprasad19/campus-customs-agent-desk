"""Campus Customs MCP server.

This is the ONLY way the agent team touches shop data. There is deliberately no
second tools layer in backend/ that reaches around this server into SQLite.

Every value returned here comes out of the database. When a row is missing the
tool reports the miss; it never substitutes a placeholder or an assumed value.

Shop rules enforced in code, not left to the model's judgement:
  * "today" is `desk.date_today`, never the real system clock
  * no payment executes without a human approval recorded outside the agents
  * a payment that would overdraw the account is refused
  * a vendor holding an unpaid invoice cannot ship
  * drafts stay on the board; nothing is emailed or sent

Reads and writes go to the WORKING COPY (data/campus_customs_new.db). The
pristine original (data/campus_customs.db) is refused as a write target.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

# Homework 5/mcp_server/server.py -> Homework 5/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

# CAMPUS_CUSTOMS_DB lets a caller point at a different file. It should still be
# a working copy, never the pristine original. A relative value is resolved
# against the project root, not the working directory, so the server behaves the
# same no matter where it is launched from.
_db_override = os.environ.get("CAMPUS_CUSTOMS_DB")
if _db_override:
    _candidate = Path(_db_override)
    DB_PATH = _candidate if _candidate.is_absolute() else (PROJECT_ROOT / _candidate)
else:
    DB_PATH = DEFAULT_DB_PATH

# The board. Drafts and approval requests are process state, not shop facts, so
# they live beside the run output rather than in the shop database.
# CAMPUS_CUSTOMS_OUTPUT_DIR exists so tests can point the board somewhere
# disposable instead of writing over a real run.
_out_override = os.environ.get("CAMPUS_CUSTOMS_OUTPUT_DIR")
if _out_override:
    _out_candidate = Path(_out_override)
    OUTPUT_DIR = _out_candidate if _out_candidate.is_absolute() else (PROJECT_ROOT / _out_candidate)
else:
    OUTPUT_DIR = PROJECT_ROOT / "output"
APPROVALS_PATH = OUTPUT_DIR / "approvals.json"
DRAFTS_PATH = OUTPUT_DIR / "drafts.json"

# The original must never be written through this server.
PROTECTED_DB_NAMES = {"campus_customs.db"}

# Where a ticket's life ends. An agent cannot move a ticket out of either of
# these on a later run; only the owner can, working at the desk.
TERMINAL_TICKET_STATUSES = {"resolved", "refused"}

mcp = FastMCP("campus-customs")


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------


def _require_db() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Shop database not found at {DB_PATH}. "
            "Copy it from data/campus_customs.db first."
        )


def _connect_ro() -> sqlite3.Connection:
    """Open the working database read-only, for tools that only look."""
    _require_db()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw() -> sqlite3.Connection:
    """Open the working database for writing, refusing the pristine original."""
    _require_db()
    if DB_PATH.name in PROTECTED_DB_NAMES:
        raise PermissionError(
            f"Refusing to write to {DB_PATH.name}. That file is the pristine "
            "original and must stay untouched; point CAMPUS_CUSTOMS_DB at the "
            "working copy data/campus_customs_new.db."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _shop_today(conn: sqlite3.Connection) -> date:
    """Return the shop's 'today' from desk.date_today.

    The shop runs on its own calendar. The real system clock is never used for
    due-date, overdue or payment-timestamp math.
    """
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("desk table has no row, so the shop date is unknown")
    return date.fromisoformat(row["date_today"])


# --------------------------------------------------------------------------
# Board helpers (approvals and drafts)
# --------------------------------------------------------------------------


def _load_board(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else [raw]


def _append_board(path: Path, record: dict[str, Any]) -> None:
    """Append one record. Existing records are never dropped."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = _load_board(path)
    records.append(record)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def _replace_board(path: Path, records: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


# ==========================================================================
# READ TOOLS
# ==========================================================================


@mcp.tool
def get_shop_date() -> dict[str, Any]:
    """Return the shop's current date from the desk.

    Every due-date and overdue judgement must be made against this date. The
    real-world calendar is not the shop's calendar.
    """
    with _connect_ro() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    if row is None:
        return {"found": False, "note": "desk table is empty."}
    return {"found": True, "date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool
def list_open_tickets() -> dict[str, Any]:
    """List every ticket still open, with the ids that link it elsewhere.

    This is the team's inbox. Use it to see what work exists before deciding
    anything.
    """
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, "
            "invoice_id, status, notes, created_at FROM tickets "
            "WHERE status = 'open' ORDER BY id"
        ).fetchall()
    return {"count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_all_tickets() -> dict[str, Any]:
    """List every ticket regardless of status, open or already dealt with.

    Use this for a board or dashboard view that has to show resolved work too.
    `list_open_tickets` is the right tool when you only want outstanding work.
    """
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, "
            "invoice_id, status, notes, created_at FROM tickets ORDER BY id"
        ).fetchall()
    tickets = [dict(r) for r in rows]
    return {
        "count": len(tickets),
        "open_count": sum(1 for t in tickets if t["status"] == "open"),
        "tickets": tickets,
    }


@mcp.tool
def get_ticket(ticket_id: int) -> dict[str, Any]:
    """Fetch one ticket by id, including its sku/size/qty and linked ids."""
    with _connect_ro() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {"found": False, "ticket_id": ticket_id, "note": "No ticket with this id."}
    return {"found": True, **dict(row)}


@mcp.tool
def check_inventory_stock(sku: str, size: str) -> dict[str, Any]:
    """Check how many units of one SKU in one size are on hand.

    Inventory is keyed on sku AND size, so stock must always be checked per
    size. A product being in stock overall says nothing about the size a
    customer asked for.

    Args:
        sku: Product code, for example "CC-TEE-WHITE".
        size: Size code, for example "S", "M", "L", "XL" or "OS".
    """
    with _connect_ro() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()

    if row is None:
        # No such sku/size. Report the miss rather than assuming zero stock.
        return {
            "found": False,
            "sku": sku,
            "size": size,
            "note": "No inventory row exists for this sku and size.",
        }
    return {"found": True, **dict(row)}


@mcp.tool
def get_sku_pricing(sku: str) -> dict[str, Any]:
    """Look up cost and list price for one SKU.

    unit_cost is what the shop paid and is the floor any discount has to clear.
    This tool reports stored prices only; it does not compute or propose a
    discounted price.
    """
    with _connect_ro() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if row is None:
        return {"found": False, "sku": sku, "note": "No pricing row exists for this sku."}
    return {
        "found": True,
        **dict(row),
        "margin_per_unit": row["list_price"] - row["unit_cost"],
    }


@mcp.tool
def get_lease_rent_due(lease_id: int) -> dict[str, Any]:
    """Look up the rent owed on a lease and how close it is to due.

    Urgency is measured against desk.date_today. monthly_rent is the amount a
    rent payment must match.
    """
    with _connect_ro() as conn:
        row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        today = _shop_today(conn)

    if row is None:
        return {"found": False, "lease_id": lease_id, "note": "No lease with this id."}

    days_until_due = (date.fromisoformat(row["next_due"]) - today).days
    return {
        "found": True,
        "lease_id": row["id"],
        "space_name": row["space_name"],
        "landlord": row["landlord"],
        "monthly_rent": row["monthly_rent"],
        "next_due": row["next_due"],
        "today": today.isoformat(),
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
        "notes": row["notes"],
    }


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict[str, Any]:
    """Report the cash available in one account.

    Cash only leaves the shop in this scenario; no revenue is modelled. Treat
    this balance as a hard ceiling on everything the team spends today.
    """
    with _connect_ro() as conn:
        row = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
    if row is None:
        return {"found": False, "account": account, "note": "No such cash account."}
    return {"found": True, "account": row["name"], "balance": row["balance"], "as_of": row["date"]}


@mcp.tool
def get_invoice(invoice_id: int) -> dict[str, Any]:
    """Fetch one vendor invoice and say whether it is overdue today."""
    with _connect_ro() as conn:
        row = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, "
            "i.status, i.description FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        today = _shop_today(conn)
    if row is None:
        return {"found": False, "invoice_id": invoice_id, "note": "No invoice with this id."}
    days_overdue = (today - date.fromisoformat(row["due_date"])).days
    return {
        "found": True,
        **dict(row),
        "today": today.isoformat(),
        "days_overdue": days_overdue,
        "is_overdue": row["status"] == "open" and days_overdue > 0,
    }


@mcp.tool
def get_vendor_status(vendor_id: int) -> dict[str, Any]:
    """Report a vendor's lead time and whether they are able to ship.

    A vendor will not ship new product while they still hold an open unpaid
    invoice, so this answers both "how long would it take" and "can they take
    the order at all". earliest_arrival_date is lead_days counted forward from
    the shop's date, and is only meaningful once the vendor is unblocked.
    """
    with _connect_ro() as conn:
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            return {"found": False, "vendor_id": vendor_id, "note": "No vendor with this id."}
        open_invoices = conn.execute(
            "SELECT id, amount, due_date, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY id",
            (vendor_id,),
        ).fetchall()
        today = _shop_today(conn)

    blocking = [dict(r) for r in open_invoices]
    can_ship = len(blocking) == 0
    earliest = today.toordinal() + vendor["lead_days"]
    return {
        "found": True,
        "vendor_id": vendor["id"],
        "name": vendor["name"],
        "specialty": vendor["specialty"],
        "lead_days": vendor["lead_days"],
        "today": today.isoformat(),
        "can_ship": can_ship,
        "blocking_open_invoices": blocking,
        "blocked_reason": None if can_ship else
            f"{vendor['name']} holds {len(blocking)} unpaid invoice(s) and will not ship until paid.",
        "earliest_arrival_date": date.fromordinal(earliest).isoformat(),
    }


@mcp.tool
def list_vendors() -> dict[str, Any]:
    """List every vendor with specialty and lead time, to choose a supplier."""
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"
        ).fetchall()
    return {"count": len(rows), "vendors": [dict(r) for r in rows]}


@mcp.tool
def list_payments() -> dict[str, Any]:
    """List every payment already made, for reconciliation and audit."""
    with _connect_ro() as conn:
        rows = conn.execute(
            "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
            "FROM payments ORDER BY id"
        ).fetchall()
    return {"count": len(rows), "payments": [dict(r) for r in rows]}


# ==========================================================================
# APPROVAL TOOLS
# ==========================================================================


@mcp.tool
def request_payment_approval(
    kind: str,
    ref_id: int,
    amount: float,
    reason: str,
    requested_by: str,
    account: str = "checking",
) -> dict[str, Any]:
    """Ask a human to approve one payment. This does NOT pay anything.

    No agent can approve its own request. The returned approval_id stays
    "pending" until a person decides on it outside the agent loop, and the pay
    tools refuse any approval_id that is not "approved".

    The request is checked for affordability at request time so a human is not
    asked to approve something the shop cannot afford.

    Args:
        kind: "invoice" or "rent".
        ref_id: The invoice id or lease id the payment settles.
        amount: Exact amount to be paid.
        reason: Why this payment should happen, in one or two sentences.
        requested_by: Which agent is asking.
        account: Cash account to draw from.
    """
    if kind not in {"invoice", "rent"}:
        return {"ok": False, "error": f"kind must be 'invoice' or 'rent', got {kind!r}."}

    with _connect_ro() as conn:
        cash = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        today = _shop_today(conn)
    if cash is None:
        return {"ok": False, "error": f"No cash account named {account!r}."}

    # One request per obligation. Two agents can each decide a bill needs paying,
    # or a re-run can ask again, and the owner would then be shown the same
    # payment twice — with nothing to stop them approving both. An invoice is
    # saved by its status flipping to `paid`, but a lease has no such field, so
    # a duplicate rent approval really would pay the landlord twice.
    for existing in _load_board(APPROVALS_PATH):
        if (
            existing.get("status") == "pending"
            and existing.get("kind") == kind
            and existing.get("ref_id") == ref_id
        ):
            return {
                "ok": True,
                "approval_id": existing["approval_id"],
                "status": "pending",
                "already_raised": True,
                "note": (
                    f"A payment of ${existing.get('amount', 0):,.2f} for {kind} #{ref_id} is already "
                    f"waiting on the owner ({existing['approval_id']}). No second request was created. "
                    "Do not raise this again; wait for the owner to decide."
                ),
            }

    approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "approval_id": approval_id,
        "category": "payment",
        "status": "pending",
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "reason": reason,
        "requested_by": requested_by,
        "requested_on_shop_date": today.isoformat(),
        "balance_at_request": cash["balance"],
        "affordable_at_request": amount <= cash["balance"],
        "approved_by": None,
        "decided_on": None,
        "decision_note": None,
        "consumed_by_payment_id": None,
    }
    _append_board(APPROVALS_PATH, record)
    return {
        "ok": True,
        "approval_id": approval_id,
        "status": "pending",
        "affordable_at_request": record["affordable_at_request"],
        "balance_at_request": cash["balance"],
        "note": (
            "Recorded on the approval board. A human must approve it before any "
            "pay tool will run. Do not assume approval."
        ),
    }


@mcp.tool
def request_price_override_approval(
    ticket_id: int,
    sku: str,
    size: str,
    qty: int,
    proposed_unit_price: float,
    reason: str,
    requested_by: str,
) -> dict[str, Any]:
    """Ask a human to approve selling a SKU below its list price. Changes nothing.

    No money leaves the shop for a discount, so this is not a payment — but it
    is still a decision only an owner should make, and it lands on the same
    approval board so there is one queue of things waiting on a person.

    The arithmetic is done here from the stored pricing rather than taken from
    the agent, so a hopeful margin cannot be talked into existence. Approving
    does NOT rewrite the pricing table: a one-off bulk deal is not a new list
    price for everyone.

    Args:
        ticket_id: The price_override ticket this settles.
        sku: Product code, for example "CC-HOOD-NAVY".
        size: Size requested.
        qty: Units the customer wants.
        proposed_unit_price: The per-unit price being recommended.
        reason: Why this price, in one or two sentences.
        requested_by: Which agent is asking.
    """
    if qty <= 0:
        return {"ok": False, "error": "qty must be a positive number of units."}
    if proposed_unit_price <= 0:
        return {"ok": False, "error": "proposed_unit_price must be greater than zero."}

    with _connect_ro() as conn:
        pricing = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        stock = conn.execute(
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        ticket = conn.execute(
            "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        today = _shop_today(conn)

    if pricing is None:
        return {"ok": False, "error": f"No pricing row exists for {sku}."}
    if ticket is None:
        return {"ok": False, "error": f"No ticket with id {ticket_id}."}

    # One decision per ticket. An agent that asks twice — because it retried, or
    # because two agents both thought it was their job — would put two identical
    # slips in front of the owner and invite them to approve the same discount
    # twice. Hand back the request already waiting instead of making another.
    for existing in _load_board(APPROVALS_PATH):
        if (
            existing.get("status") == "pending"
            and existing.get("kind") == "price_override"
            and existing.get("ticket_id") == ticket_id
        ):
            return {
                "ok": True,
                "approval_id": existing["approval_id"],
                "status": "pending",
                "already_raised": True,
                "existing_unit_price": existing.get("proposed_unit_price"),
                "note": (
                    f"Ticket {ticket_id} already has a price decision waiting on the "
                    f"owner at ${existing.get('proposed_unit_price'):,.2f} per unit "
                    f"({existing['approval_id']}). No second request was created. "
                    "Do not raise this again; wait for the owner to decide."
                ),
            }

    unit_cost = pricing["unit_cost"]
    list_price = pricing["list_price"]
    on_hand = stock["qty"] if stock else 0

    margin_per_unit = round(proposed_unit_price - unit_cost, 2)
    approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "approval_id": approval_id,
        "category": "decision",
        "status": "pending",
        "kind": "price_override",
        "ref_id": ticket_id,
        "ticket_id": ticket_id,
        "sku": sku,
        "size": size,
        "qty": qty,
        "proposed_unit_price": proposed_unit_price,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "discount_per_unit": round(list_price - proposed_unit_price, 2),
        "discount_percent": round((list_price - proposed_unit_price) / list_price * 100, 1),
        "margin_per_unit": margin_per_unit,
        "total_at_proposed": round(proposed_unit_price * qty, 2),
        "total_at_list": round(list_price * qty, 2),
        "total_cost": round(unit_cost * qty, 2),
        "total_margin": round(margin_per_unit * qty, 2),
        "below_cost": proposed_unit_price < unit_cost,
        "qty_on_hand": on_hand,
        "short_by": max(0, qty - on_hand),
        "can_supply_in_full": on_hand >= qty,
        "reason": reason,
        "requested_by": requested_by,
        "requested_on_shop_date": today.isoformat(),
        "approved_by": None,
        "decided_on": None,
        "decision_note": None,
        "applied_to_ticket": None,
    }
    _append_board(APPROVALS_PATH, record)
    return {
        "ok": True,
        "approval_id": approval_id,
        "status": "pending",
        "below_cost": record["below_cost"],
        "margin_per_unit": margin_per_unit,
        "total_margin": record["total_margin"],
        "can_supply_in_full": record["can_supply_in_full"],
        "short_by": record["short_by"],
        "note": (
            "Recorded on the approval board as a decision for a human. Nothing "
            "has been promised to the customer and no price has changed."
        ),
    }


@mcp.tool
def get_approval_status(approval_id: str) -> dict[str, Any]:
    """Check whether a human has decided on a payment approval request."""
    for record in _load_board(APPROVALS_PATH):
        if record.get("approval_id") == approval_id:
            return {"found": True, **record}
    return {"found": False, "approval_id": approval_id, "note": "No such approval request."}


@mcp.tool
def list_approvals() -> dict[str, Any]:
    """List every approval request and its current decision."""
    records = _load_board(APPROVALS_PATH)
    return {"count": len(records), "approvals": records}


def _claim_approval(approval_id: str, kind: str, ref_id: int, amount: float) -> dict[str, Any]:
    """Validate an approval before a payment runs. Returns an error dict or the record."""
    records = _load_board(APPROVALS_PATH)
    for record in records:
        if record.get("approval_id") != approval_id:
            continue
        if record.get("status") != "approved":
            return {"error": (
                f"Approval {approval_id} is '{record.get('status')}', not 'approved'. "
                "A human has not cleared this payment, so it will not run."
            )}
        if record.get("consumed_by_payment_id") is not None:
            return {"error": (
                f"Approval {approval_id} was already used for payment "
                f"{record['consumed_by_payment_id']}. Each approval pays once."
            )}
        if record.get("kind") != kind or record.get("ref_id") != ref_id:
            return {"error": (
                f"Approval {approval_id} covers {record.get('kind')} #{record.get('ref_id')}, "
                f"not {kind} #{ref_id}. Approvals are not transferable."
            )}
        if abs(float(record.get("amount", 0)) - float(amount)) > 0.005:
            return {"error": (
                f"Approval {approval_id} is for ${record.get('amount'):,.2f} but this payment "
                f"is ${amount:,.2f}. The amount must match exactly."
            )}
        return {"record": record, "all_records": records}
    return {"error": f"No approval request found with id {approval_id}."}


# ==========================================================================
# PAYMENT TOOLS
# ==========================================================================


def _execute_payment(
    kind: str, ref_id: int, amount: float, approval_id: str, account: str
) -> dict[str, Any]:
    """Shared payment path: approval gate, then cash gate, then write."""
    claim = _claim_approval(approval_id, kind, ref_id, amount)
    if "error" in claim:
        return {"paid": False, "refused": True, "reason": claim["error"]}
    approval = claim["record"]

    conn = _connect_rw()
    try:
        balance_row = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if balance_row is None:
            return {"paid": False, "refused": True, "reason": f"No cash account named {account!r}."}
        balance = balance_row["balance"]

        # Hard rule: no negative balances, ever.
        if amount > balance:
            return {
                "paid": False,
                "refused": True,
                "reason": (
                    f"Refused: paying ${amount:,.2f} from {account} would overdraw an account "
                    f"holding ${balance:,.2f}. The shop does not go negative."
                ),
                "balance": balance,
                "shortfall": round(amount - balance, 2),
            }

        today = _shop_today(conn)

        # Second line of defence. Even with a valid, unused approval in hand,
        # the same obligation must not be settled twice on the same day. An
        # invoice is already protected by its status, but rent is not.
        already = conn.execute(
            "SELECT id, amount FROM payments WHERE kind = ? AND ref_id = ? AND paid_at = ?",
            (kind, ref_id, today.isoformat()),
        ).fetchone()
        if already is not None:
            return {
                "paid": False,
                "refused": True,
                "reason": (
                    f"Refused: {kind} #{ref_id} was already paid today "
                    f"(payment #{already['id']}, ${already['amount']:,.2f}). "
                    "The shop does not pay the same obligation twice."
                ),
                "existing_payment_id": already["id"],
            }

        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, today.isoformat(), approval["approved_by"]),
        )
        payment_id = cur.lastrowid

        new_balance = round(balance - amount, 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today.isoformat(), account),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        conn.commit()
    finally:
        conn.close()

    # Burn the approval so it cannot pay twice.
    for record in claim["all_records"]:
        if record.get("approval_id") == approval_id:
            record["consumed_by_payment_id"] = payment_id
    _replace_board(APPROVALS_PATH, claim["all_records"])

    return {
        "paid": True,
        "payment_id": payment_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "paid_at": today.isoformat(),
        "approved_by": approval["approved_by"],
        "approval_id": approval_id,
        "balance_before": balance,
        "balance_after": new_balance,
        "tables_updated": ["payments", "cash_accounts"] + (["invoices"] if kind == "invoice" else []),
    }


@mcp.tool
def pay_invoice(invoice_id: int, approval_id: str, account: str = "checking") -> dict[str, Any]:
    """Pay a vendor invoice in full, given a human-approved approval_id.

    Refuses unless a person approved this exact invoice for this exact amount,
    and refuses again if the payment would overdraw the account. On success it
    writes a payments row, lowers the cash balance and marks the invoice paid.
    """
    with _connect_ro() as conn:
        invoice = conn.execute(
            "SELECT id, amount, status FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
    if invoice is None:
        return {"paid": False, "refused": True, "reason": f"No invoice with id {invoice_id}."}
    if invoice["status"] != "open":
        return {
            "paid": False,
            "refused": True,
            "reason": f"Invoice {invoice_id} is already '{invoice['status']}'. Nothing to pay.",
        }
    return _execute_payment("invoice", invoice_id, invoice["amount"], approval_id, account)


@mcp.tool
def pay_rent(lease_id: int, approval_id: str, account: str = "checking") -> dict[str, Any]:
    """Pay one month's rent on a lease, given a human-approved approval_id.

    The amount is taken from the lease, not from the agent, so it cannot drift.
    Refuses without human approval and refuses if it would overdraw. On success
    it writes a payments row and lowers the cash balance. The leases table has
    no status or paid-through column, so nothing there is altered.
    """
    with _connect_ro() as conn:
        lease = conn.execute(
            "SELECT id, monthly_rent FROM leases WHERE id = ?", (lease_id,)
        ).fetchone()
    if lease is None:
        return {"paid": False, "refused": True, "reason": f"No lease with id {lease_id}."}
    return _execute_payment("rent", lease_id, lease["monthly_rent"], approval_id, account)


# ==========================================================================
# FULFILMENT AND BOARD TOOLS
# ==========================================================================


@mcp.tool
def reduce_inventory_for_sale(sku: str, size: str, qty: int, ticket_id: int) -> dict[str, Any]:
    """Take units off the shelf to fulfil a customer order.

    Refuses to move more units than are physically on hand; stock never goes
    negative. No money is recorded, because this scenario does not model
    revenue coming in.
    """
    if qty <= 0:
        return {"ok": False, "refused": True, "reason": "qty must be a positive number of units."}

    conn = _connect_rw()
    try:
        row = conn.execute(
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if row is None:
            return {
                "ok": False,
                "refused": True,
                "reason": f"No inventory row for {sku} size {size}.",
            }
        on_hand = row["qty"]
        if qty > on_hand:
            return {
                "ok": False,
                "refused": True,
                "reason": (
                    f"Refused: ticket {ticket_id} wants {qty} of {sku}/{size} but only "
                    f"{on_hand} are on hand. Stock cannot go negative."
                ),
                "on_hand": on_hand,
                "short_by": qty - on_hand,
            }
        remaining = on_hand - qty
        conn.execute(
            "UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?", (remaining, sku, size)
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "sku": sku,
        "size": size,
        "qty_taken": qty,
        "qty_before": on_hand,
        "qty_remaining": remaining,
        "ticket_id": ticket_id,
        "tables_updated": ["inventory"],
    }


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str, updated_by: str) -> dict[str, Any]:
    """Move a ticket to a new status and append a note explaining why.

    Allowed statuses and what each one means:

      open                 still being worked
      waiting_on_approval  a decision is sitting with a human right now
      waiting_on_vendor    an order has been placed and the shop is waiting
      refused              the shop will not do this, for a stated reason
      resolved             CLOSED FROM THE SHOP'S SIDE: everything the shop can
                           do today has been done, and no further action is
                           available to it

    `resolved` does not promise that the customer has their goods. A shop can
    finish its side of a job and still be waiting on the world — stock that has
    not arrived, money it does not have. When that is the case the note must say
    so plainly, because the note is where the truth lives. Closing a ticket with
    a note that hides an unmet promise is the one thing this tool must never be
    used for.

    The note is appended to the ticket's existing notes rather than overwriting
    them, so the ticket keeps its history.

    `resolved` and `refused` are final. Once a ticket reaches either, this tool
    will not move it again and you should leave it alone: a closed ticket is a
    closed ticket, and a refusal was a person's decision, not yours to overturn.
    Only the owner, working at the desk, can reopen one.
    """
    allowed = {"open", "waiting_on_approval", "waiting_on_vendor", "resolved", "refused"}
    if status not in allowed:
        return {"ok": False, "reason": f"status must be one of {sorted(allowed)}."}

    conn = _connect_rw()
    try:
        row = conn.execute(
            "SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return {"ok": False, "reason": f"No ticket with id {ticket_id}."}

        # A closed ticket stays closed. `resolved` means the shop has run out of
        # moves and `refused` means a person said no, so neither is an agent's to
        # reverse on a later run. The desk stamps its own updates with
        # "via the desk", which is how a human override gets through.
        at_the_desk = "via the desk" in (updated_by or "")
        if row["status"] in TERMINAL_TICKET_STATUSES and not at_the_desk:
            return {
                "ok": False,
                "ticket_id": ticket_id,
                "status_before": row["status"],
                "status_after": row["status"],
                "reason": (
                    f"Ticket {ticket_id} is already '{row['status']}', which is final. "
                    "A closed ticket is not reopened by an agent and a refusal is not "
                    "overturned by one. Leave this ticket as it is and report that it "
                    "was already closed. Only the owner can change it from the desk."
                ),
            }

        today = _shop_today(conn)
        stamped = f"[{today.isoformat()} {updated_by}] {note}"
        combined = f"{row['notes']}\n{stamped}" if row["notes"] else stamped
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, combined, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "ticket_id": ticket_id,
        "status_before": row["status"],
        "status_after": status,
        "note_appended": stamped,
        "tables_updated": ["tickets"],
    }


@mcp.tool
def save_draft_message(
    ticket_id: int, audience: str, subject: str, body: str, author: str
) -> dict[str, Any]:
    """Save a message draft to the board. Nothing is sent.

    Customers are not emailed and vendors are not contacted in this scenario.
    Drafts are written down for a human to review and send later.
    """
    with _connect_ro() as conn:
        today = _shop_today(conn)

    draft_id = f"DRAFT-{uuid.uuid4().hex[:6].upper()}"
    record = {
        "draft_id": draft_id,
        "ticket_id": ticket_id,
        "audience": audience,
        "subject": subject,
        "body": body,
        "author": author,
        "shop_date": today.isoformat(),
        "delivery_status": "not_sent_draft_only",
    }
    _append_board(DRAFTS_PATH, record)
    return {
        "ok": True,
        "draft_id": draft_id,
        "delivery_status": "not_sent_draft_only",
        "note": "Saved to output/drafts.json for human review. No message was sent.",
    }


if __name__ == "__main__":
    mcp.run()
