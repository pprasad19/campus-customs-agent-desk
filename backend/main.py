"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

That serves http://localhost:8000 for the React frontend to call.

The API never reads or writes shop data directly. Every shop fact and every
payment goes through the same MCP server the agents use, so there is still one
layer between the database and everything else. The only files the API touches
on its own are the ones it produced: the audit trail, and the database copy made
by a reset.

One deliberate asymmetry: the agents can only *prepare* a payment, by calling
request_payment_approval. Cash moves when a human clicks approve, which lands on
POST /approvals/{approval_id}/approve below.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# uvicorn is started from inside backend/, so main is a top-level module. Put
# the project root on the path first, then import the package normally.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend.config import AUDIT_PATH, MODEL_NAME, OUTPUT_DIR, PROJECT_ROOT  # noqa: E402
from backend.audit import AuditTrail  # noqa: E402
from backend.mcp_link import link  # noqa: E402
from backend.run_team import run_shift  # noqa: E402

ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"
APPROVALS_PATH = OUTPUT_DIR / "approvals.json"

# Agent runs are serialised. Two runs at once would interleave their writes to
# the audit trail and race each other on the cash balance.
run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await link.open()
    try:
        yield
    finally:
        await link.close()


app = FastAPI(
    title="Campus Customs backend",
    description="Backend for the shop dashboard. All shop access goes through MCP.",
    version="1.0.0",
    lifespan=lifespan,
)

# The React desk is served by Vite on a different port, so the browser treats
# every call to this API as cross-origin and blocks it unless the origin is
# named here. Both spellings of localhost are listed because the browser treats
# them as different origins.
# Vite prefers 5173 but steps to 5174/5175 if that port is already taken, so
# all three are allowed; otherwise the desk would load and then be unable to
# fetch anything. 4173 is the preview server for a production build.
ALLOWED_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (5173, 5174, 5175, 4173)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Response shapes
# --------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    approved_by: str = Field(description="Name of the person approving. Required.")
    note: str | None = Field(default=None, description="Optional reason for the decision.")


class RejectRequest(BaseModel):
    rejected_by: str
    note: str | None = None


# --------------------------------------------------------------------------
# 1. The tickets board
# --------------------------------------------------------------------------


@app.get("/tickets", summary="The three tickets and whether each is still open")
async def get_tickets() -> dict[str, Any]:
    """Every ticket with its current status, for the board."""
    data = await link.call("list_all_tickets")
    tickets = data.get("tickets", [])
    for ticket in tickets:
        # The board wants a simple open/closed read as well as the raw status.
        ticket["is_open"] = ticket["status"] == "open"
        ticket["is_resolved"] = ticket["status"] == "resolved"
    shop = await link.call("get_shop_date")
    return {
        "shop_date": shop.get("date_today"),
        "count": len(tickets),
        "open_count": sum(1 for t in tickets if t["is_open"]),
        "tickets": tickets,
    }


# --------------------------------------------------------------------------
# 2. Run the agent team on one ticket
# --------------------------------------------------------------------------


@app.post("/tickets/{ticket_id}/run", summary="Run the agent team on one ticket")
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Work a single ticket with the five-agent team.

    This makes real model calls and can take a while. Runs are serialised, so a
    second request waits rather than racing the first.
    """
    board = await link.call("get_ticket", ticket_id=ticket_id)
    if not board.get("found"):
        raise HTTPException(status_code=404, detail=f"No ticket with id {ticket_id}.")

    if run_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="A run is already in progress. Wait for it to finish before starting another.",
        )

    run_id = f"RUN-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    async with run_lock:
        try:
            report = await run_shift(run_id, ticket_id=ticket_id)
        except Exception as exc:  # noqa: BLE001 - surface the failure to the dashboard
            raise HTTPException(
                status_code=500,
                detail=f"Agent run {run_id} failed: {type(exc).__name__}: {exc}",
            ) from exc

    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "model": MODEL_NAME,
        "report": report.model_dump() if report is not None else None,
    }


# --------------------------------------------------------------------------
# 3. Recent agent events
# --------------------------------------------------------------------------


@app.get("/events", summary="Recent agent events, for refreshing the board")
async def get_events(
    limit: int = Query(default=80, ge=1, le=1000, description="How many recent steps to return."),
    run_id: str | None = Query(default=None, description="Restrict to one run."),
) -> dict[str, Any]:
    """What each agent said and which tools it used, newest last.

    Read from output/audit_trail.json, which only ever grows, so this is the
    same history the audit trail holds rather than a separate log.
    """
    import json

    if not AUDIT_PATH.exists():
        return {"count": 0, "total_steps": 0, "runs": [], "events": []}

    try:
        steps = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="audit_trail.json is not valid JSON.")
    if not isinstance(steps, list):
        steps = [steps]

    if run_id:
        steps = [s for s in steps if s.get("run_id") == run_id]

    runs: list[str] = []
    for step in steps:
        rid = step.get("run_id")
        if rid and rid not in runs:
            runs.append(rid)

    recent = steps[-limit:]
    return {
        "count": len(recent),
        "total_steps": len(steps),
        "runs": runs,
        "latest_run": runs[-1] if runs else None,
        "events": recent,
    }


# --------------------------------------------------------------------------
# 4. Human approval — the only thing that moves cash
# --------------------------------------------------------------------------


@app.post("/approvals/{approval_id}/approve", summary="Approve a prepared payment and pay it")
async def approve_payment(approval_id: str, body: ApproveRequest) -> dict[str, Any]:
    """Record a human approval, then execute the payment.

    The agents can only prepare a payment; this is where cash actually changes.
    The sequence is deliberate:

      1. mark the request approved, naming the person responsible
      2. call the matching MCP pay tool with that approval id

    Step 2 re-checks everything — that the approval is approved, unused, and
    matches this exact payment, and that the balance covers it. A refusal there
    is reported back rather than worked around.
    """
    import json

    if not body.approved_by.strip():
        raise HTTPException(status_code=400, detail="approved_by is required; an approval must name a person.")

    records = _load_approvals()
    record = next((r for r in records if r.get("approval_id") == approval_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No approval request with id {approval_id}.")
    if record.get("status") != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval {approval_id} is already '{record['status']}'.",
        )

    record["status"] = "approved"
    record["approved_by"] = body.approved_by
    record["decided_on"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["decision_note"] = body.note
    APPROVALS_PATH.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    # A decision is not a payment. Approving a price override moves no cash; it
    # settles the ticket with the agreed terms written into its history. The
    # pricing table is deliberately left alone — a one-off bulk deal is not a
    # new list price for every customer.
    if record.get("category") == "decision":
        return await _apply_decision(record, body.approved_by, records)

    # Otherwise it is a payment: execute it through the MCP server.
    kind = record.get("kind")
    if kind == "invoice":
        result = await link.call(
            "pay_invoice",
            invoice_id=record["ref_id"],
            approval_id=approval_id,
            account=record.get("account", "checking"),
        )
    elif kind == "rent":
        result = await link.call(
            "pay_rent",
            lease_id=record["ref_id"],
            approval_id=approval_id,
            account=record.get("account", "checking"),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown payment kind {kind!r}.")

    # A paid obligation has to be reflected on the ticket that raised it,
    # otherwise the board keeps saying "waiting on you" about something already
    # settled. Only do this once the payment actually went through.
    ticket_update = None
    if result.get("paid"):
        ticket_update = await _settle_ticket_for_payment(record, result, body.approved_by)

    balance = await link.call("get_cash_balance", account=record.get("account", "checking"))
    return {
        "approval_id": approval_id,
        "approved_by": body.approved_by,
        "payment": result,
        "paid": bool(result.get("paid")),
        "refused_reason": result.get("reason"),
        "balance_after": balance.get("balance"),
        "ticket_update": ticket_update,
    }


async def _settle_ticket_for_payment(
    record: dict[str, Any], payment: dict[str, Any], approved_by: str
) -> dict[str, Any] | None:
    """Move the ticket a payment belongs to, if there is one.

    The two kinds settle differently, and the difference matters:

    * **Rent** discharges the obligation outright. The rent notice is done.
    * **An invoice** does not. Paying Bulldog Print Co clears the debt and
      unblocks them, but the customer still has no tee — so that ticket moves to
      `waiting_on_vendor`, not `resolved`. Marking it resolved would claim an
      order was filled when nothing has shipped.
    """
    kind, ref_id = record.get("kind"), record.get("ref_id")
    board = await link.call("list_all_tickets")

    if kind == "rent":
        match = next(
            (t for t in board.get("tickets", []) if t.get("lease_id") == ref_id), None
        )
        status = "resolved"
        note = (
            f"Rent of ${payment['amount']:,.2f} paid in full on {payment['paid_at']} "
            f"(payment #{payment['payment_id']}, approved by {approved_by}). "
            "Nothing further is owed on this notice."
        )
    elif kind == "invoice":
        match = next(
            (t for t in board.get("tickets", []) if t.get("invoice_id") == ref_id), None
        )
        status = "waiting_on_vendor"
        note = (
            f"Invoice {ref_id} settled for ${payment['amount']:,.2f} "
            f"(payment #{payment['payment_id']}, approved by {approved_by}), so the "
            "vendor is no longer blocked. The order itself is still outstanding until "
            "stock arrives."
        )
    else:
        return None

    if match is None or match.get("status") in {"resolved", "refused"}:
        return None

    return await link.call(
        "update_ticket_status",
        ticket_id=match["id"],
        status=status,
        note=note,
        updated_by=f"{approved_by} (owner, via the desk)",
    )


@app.post("/approvals/{approval_id}/reject", summary="Reject a prepared payment")
async def reject_payment(approval_id: str, body: RejectRequest) -> dict[str, Any]:
    """Turn a prepared payment down. No cash moves."""
    import json

    records = _load_approvals()
    record = next((r for r in records if r.get("approval_id") == approval_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No approval request with id {approval_id}.")
    if record.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Approval {approval_id} is already '{record['status']}'.")

    record["status"] = "rejected"
    record["approved_by"] = None          # nobody approved it
    record["rejected_by"] = body.rejected_by
    record["decided_on"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["decision_note"] = body.note
    APPROVALS_PATH.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    # A declined discount is still an answer the ticket deserves to carry.
    if record.get("category") == "decision":
        ticket_id = record.get("ticket_id") or record.get("ref_id")
        note = (
            f"Price override DECLINED by {body.rejected_by}: "
            f"${record['proposed_unit_price']:,.2f} per unit on {record['sku']} "
            f"was not accepted. The list price of ${record['list_price']:,.2f} stands."
        )
        if body.note:
            note += f" Reason: {body.note}"
        await link.call(
            "update_ticket_status",
            ticket_id=ticket_id,
            status="refused",
            note=note,
            updated_by=f"{body.rejected_by} (owner, via the desk)",
        )
        return {
            "approval_id": approval_id,
            "status": "rejected",
            "rejected_by": body.rejected_by,
            "ticket_id": ticket_id,
            "note": "Declined. The list price stands and the ticket records the refusal.",
        }

    # A declined payment is a decision too. Leaving the ticket on
    # `waiting_on_approval` would tell the owner they still owe an answer to
    # something they have already answered.
    ticket_update = await _settle_ticket_after_decline(record, body.rejected_by, body.note)
    return {
        "approval_id": approval_id,
        "status": "rejected",
        "rejected_by": body.rejected_by,
        "ticket_update": ticket_update,
    }


async def _settle_ticket_after_decline(
    record: dict[str, Any], rejected_by: str, note: str | None
) -> dict[str, Any] | None:
    """Move the ticket behind a declined payment to its honest end state.

    A declined payment is a decision, and the ticket records it as one: the
    status becomes `refused` — "the shop will not do this, for a stated reason".
    That is true of both kinds, though the consequence differs and the note says
    which:

    * **An invoice** is what unblocks a vendor, so declining it closes off the
      route to the goods and the customer order cannot be filled.
    * **Rent** does not disappear when you decline it. The notice is answered,
      but the money is still owed, and the note says so plainly.

    Neither becomes `resolved`. Nothing was delivered and nothing was paid;
    claiming otherwise would be the one thing this board must never do.
    """
    kind, ref_id = record.get("kind"), record.get("ref_id")
    board = await link.call("list_all_tickets")
    amount = record.get("amount", 0)
    status = "refused"

    if kind == "rent":
        match = next((t for t in board.get("tickets", []) if t.get("lease_id") == ref_id), None)
        text = (
            f"Payment REFUSED by {rejected_by}: rent of ${amount:,.2f} on lease {ref_id} "
            f"was not approved ({record['approval_id']}). No money moved. Note that the rent "
            "is still owed to the landlord — refusing the payment answers this notice but does "
            "not discharge the debt."
        )
    elif kind == "invoice":
        match = next((t for t in board.get("tickets", []) if t.get("invoice_id") == ref_id), None)
        text = (
            f"Payment REFUSED by {rejected_by}: invoice {ref_id} for ${amount:,.2f} was not "
            f"approved ({record['approval_id']}). No money moved. The vendor stays blocked while "
            "that invoice is unpaid, so the goods cannot be sourced and this order is refused. "
            "The customer should be told it cannot be filled."
        )
    else:
        return None

    if match is None or match.get("status") in {"resolved", "refused"}:
        return None

    if note:
        text += f" Reason: {note}"

    return await link.call(
        "update_ticket_status",
        ticket_id=match["id"],
        status=status,
        note=text,
        updated_by=f"{rejected_by} (owner, via the desk)",
    )


async def _apply_decision(
    record: dict[str, Any], approved_by: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Settle an approved non-payment decision, such as a price override.

    The outcome is written onto the ticket through the MCP server, so the terms
    the owner agreed to are part of the ticket's permanent history rather than
    living only on the approval board.
    """
    import json

    ticket_id = record.get("ticket_id") or record.get("ref_id")
    note = (
        f"Price override APPROVED by {approved_by}: {record['qty']} x {record['sku']} "
        f"size {record['size']} at ${record['proposed_unit_price']:,.2f} per unit "
        f"(list ${record['list_price']:,.2f}, cost ${record['unit_cost']:,.2f}), "
        f"leaving ${record['total_margin']:,.2f} total margin. "
        f"Stored list price unchanged. Approval {record['approval_id']}."
    )
    if record.get("short_by"):
        note += (
            f" Note: only {record['qty_on_hand']} on hand, short by "
            f"{record['short_by']} — the shortfall still needs sourcing."
        )

    applied = await link.call(
        "update_ticket_status",
        ticket_id=ticket_id,
        status="resolved" if record.get("can_supply_in_full") else "waiting_on_vendor",
        note=note,
        updated_by=f"{approved_by} (owner, via the desk)",
    )

    for r in records:
        if r.get("approval_id") == record["approval_id"]:
            r["applied_to_ticket"] = ticket_id
    APPROVALS_PATH.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    balance = await link.call("get_cash_balance", account="checking")
    return {
        "approval_id": record["approval_id"],
        "approved_by": approved_by,
        "paid": False,
        "decision_applied": True,
        "kind": record.get("kind"),
        "ticket_id": ticket_id,
        "ticket_update": applied,
        "agreed_unit_price": record.get("proposed_unit_price"),
        "total_margin": record.get("total_margin"),
        "refused_reason": None,
        "balance_after": balance.get("balance"),
        "note": "No cash moved. A discount is a pricing decision, not a payment.",
    }


def _load_approvals() -> list[dict[str, Any]]:
    import json

    if not APPROVALS_PATH.exists():
        return []
    raw = json.loads(APPROVALS_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else [raw]


# --------------------------------------------------------------------------
# 5. Cash
# --------------------------------------------------------------------------


@app.get("/cash", summary="Current checking balance from cash_accounts")
async def get_cash(account: str = Query(default="checking")) -> dict[str, Any]:
    """The balance, plus what is queued against it.

    Pending approvals are included because they are claims on this exact
    balance: the dashboard needs their ids to offer an approve button, and the
    number is not meaningful without knowing what is waiting to come out of it.
    """
    balance = await link.call("get_cash_balance", account=account)
    if not balance.get("found"):
        raise HTTPException(status_code=404, detail=f"No cash account named {account!r}.")

    payments = await link.call("list_payments")
    approvals = _load_approvals()
    pending = [a for a in approvals if a.get("status") == "pending"]
    # Only payments are claims on the balance. A pending price override is
    # waiting on a person too, but approving it moves no cash, so counting it
    # here would misstate what the shop is about to spend.
    pending_total = sum(
        float(a.get("amount") or 0)
        for a in pending
        if a.get("category", "payment") == "payment"
    )

    return {
        "account": balance["account"],
        "balance": balance["balance"],
        "as_of_shop_date": balance.get("as_of"),
        "payments_made": payments.get("count", 0),
        "total_paid_out": round(sum(float(p["amount"]) for p in payments.get("payments", [])), 2),
        "pending_approvals": pending,
        "pending_approval_total": round(pending_total, 2),
        "balance_if_all_pending_paid": round(balance["balance"] - pending_total, 2),
    }


# --------------------------------------------------------------------------
# 6. Reset
# --------------------------------------------------------------------------


@app.post("/reset", summary="Restore the database to its original values")
async def reset_database(clear_boards: bool = Query(default=True)) -> dict[str, Any]:
    """Restore the working copy from the pristine original, for a fresh run.

    The audit trail is deliberately NOT cleared. It is the record of what the
    agents have done across every run, and wiping it on reset would destroy the
    evidence a reset exists to make repeatable.

    The approval and draft boards ARE cleared by default, because they refer to
    invoices and tickets whose state has just been rolled back; leaving a stale
    approved request pointing at a now-unpaid invoice would be a live hazard.
    """
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail=f"Original database missing at {ORIGINAL_DB}.")

    # Drop the MCP connection first: the server holds the database open.
    await link.close()
    try:
        shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    finally:
        await link.open()

    cleared = []
    if clear_boards:
        for board in (APPROVALS_PATH, OUTPUT_DIR / "drafts.json"):
            if board.exists():
                board.unlink()
                cleared.append(board.name)

    balance = await link.call("get_cash_balance", account="checking")
    tickets = await link.call("list_all_tickets")

    # Mark the reset in the audit trail. The trail itself is never wiped — it is
    # the record of everything the agents have done — but the board must not go
    # on showing runs from before the shop was rolled back, or a freshly reset
    # desk looks like it has already been worked. Everything before this line
    # belongs to a previous life of the database.
    shop = await link.call("get_shop_date")
    AuditTrail(
        run_id=f"RESET-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}",
        shop_date=shop.get("date_today", ""),
    ).record(
        agent="system", caller="human", depth=0, step_type="database_reset",
        detail={
            "restored_from": ORIGINAL_DB.name,
            "restored_to": WORKING_DB.name,
            "boards_cleared": cleared,
            "balance_after_reset": balance.get("balance"),
            "note": "Runs recorded before this point describe a database state that no longer exists.",
        },
    )

    return {
        "reset": True,
        "restored_from": ORIGINAL_DB.name,
        "restored_to": WORKING_DB.name,
        "boards_cleared": cleared,
        "audit_trail_preserved": AUDIT_PATH.name,
        "balance": balance.get("balance"),
        "open_tickets": tickets.get("open_count"),
    }


# --------------------------------------------------------------------------


@app.get("/", summary="What this API offers")
async def root() -> dict[str, Any]:
    return {
        "service": "Campus Customs backend",
        "model": MODEL_NAME,
        "database": WORKING_DB.name,
        "routes": {
            "GET  /tickets": "the three tickets and whether each is open or resolved",
            "POST /tickets/{id}/run": "run the agent team on one ticket",
            "GET  /events": "recent agent events for refreshing the board",
            "POST /approvals/{id}/approve": "human approves a prepared payment; this is what moves cash",
            "POST /approvals/{id}/reject": "human turns a prepared payment down",
            "GET  /cash": "current checking balance and what is queued against it",
            "POST /reset": "restore the database to original values for a fresh run",
        },
    }
