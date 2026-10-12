"""Run the Campus Customs agent team over the open tickets.

Usage, from the Homework 5 folder:

    .venv/Scripts/python.exe -m backend.run_team
    .venv/Scripts/python.exe -m backend.run_team --reset

--reset restores data/campus_customs_new.db from the pristine original first,
which is what the shop rules ask for before a full ticket-resolving run. The
audit trail is never reset; it keeps growing across runs.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

from .audit import AuditTrail, usage_dict
from .config import (
    AUDIT_PATH,
    MAX_DELEGATIONS_PER_RUN,
    MAX_DELEGATION_DEPTH,
    MODEL_NAME,
    OUTPUT_DIR,
    PROJECT_ROOT,
    TEAM_USAGE_LIMITS,
)
from .models import ShiftReport, TeamDeps
from .team import build_team

ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"

OPENING_INSTRUCTION = """Work today's shift at Campus Customs.

Start by establishing the shop's date and the cash balance, then list the open
tickets. Work each ticket to a defensible conclusion, delegating to your
specialists where the work is theirs. Record the real state of each ticket in
the database before you finish, and produce your shift report.
"""

SINGLE_TICKET_INSTRUCTION = """Work ticket {ticket_id} at Campus Customs, and only that ticket.

Start by establishing the shop's date and the cash balance, then read ticket
{ticket_id} with get_ticket. Work it to a defensible conclusion, delegating only
where the work genuinely belongs to a specialist. Record the real state of the
ticket in the database before you finish.

Other tickets are open and competing for the same cash. Do not work them, but do
take them into account when judging what this one can afford.

Produce your shift report covering this ticket alone.
"""


def reset_working_database() -> None:
    """Restore the working copy from the pristine original."""
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database missing at {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    print(f"reset: {WORKING_DB.name} restored from {ORIGINAL_DB.name}")


def read_shop_date() -> str:
    conn = sqlite3.connect(f"file:{WORKING_DB}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()[0]
    finally:
        conn.close()


def read_cash() -> float:
    conn = sqlite3.connect(f"file:{WORKING_DB}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT balance FROM cash_accounts WHERE name='checking'"
        ).fetchone()[0]
    finally:
        conn.close()


async def run_shift(run_id: str, ticket_id: int | None = None) -> ShiftReport | None:
    """Run the team over the whole shift, or over one ticket when given an id."""
    shop_date = read_shop_date()
    trail = AuditTrail(run_id=run_id, shop_date=shop_date)

    trail.record(
        agent="system", caller="human", depth=0, step_type="run_started",
        detail={
            "model": MODEL_NAME,
            "provider": "portkey",
            "database": str(WORKING_DB.relative_to(PROJECT_ROOT)),
            "shop_date": shop_date,
            "scope": f"ticket {ticket_id}" if ticket_id else "all open tickets",
            "cash_at_start": read_cash(),
            "limits": {
                "max_delegation_depth": MAX_DELEGATION_DEPTH,
                "max_delegations_per_run": MAX_DELEGATIONS_PER_RUN,
                "request_limit": TEAM_USAGE_LIMITS.request_limit,
                "tool_calls_limit": TEAM_USAGE_LIMITS.tool_calls_limit,
                "total_tokens_limit": TEAM_USAGE_LIMITS.total_tokens_limit,
            },
            "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )

    agents = build_team(trail)
    boss = agents["boss"]
    deps = TeamDeps(
        run_id=run_id,
        shop_date=shop_date,
        depth=0,
        caller="human",
        max_depth=MAX_DELEGATION_DEPTH,
        delegation_budget=MAX_DELEGATIONS_PER_RUN,
    )

    report: ShiftReport | None = None
    async with contextlib.AsyncExitStack() as stack:
        # Enter the MCP toolsets once for the whole run, so the five agents
        # share a single server process instead of starting one each.
        for toolset in boss.toolsets:
            with contextlib.suppress(AttributeError):
                await stack.enter_async_context(toolset)

        try:
            instruction = (
                SINGLE_TICKET_INSTRUCTION.format(ticket_id=ticket_id)
                if ticket_id is not None
                else OPENING_INSTRUCTION
            )
            result = await boss.run(
                instruction,
                deps=deps,
                usage_limits=TEAM_USAGE_LIMITS,
                # Without this the Boss's whole history only lands when the run
                # ends, and the dashboard shows an empty floor throughout.
                event_stream_handler=trail.live_handler(
                    agent="boss", caller="human", depth=0
                ),
            )
            trail.record_agent_messages(
                agent="boss", caller="human", depth=0, messages=result.new_messages()
            )
            report = result.output
            trail.record(
                agent="boss", caller="human", depth=0, step_type="agent_finished",
                detail={"shift_report": report.model_dump()},
                usage=usage_dict(result.usage),
            )
        except Exception as exc:  # noqa: BLE001 - the failure must be auditable
            trail.record(
                agent="boss", caller="human", depth=0, step_type="error",
                detail={"exception": type(exc).__name__, "message": str(exc)},
            )
            trail.record(
                agent="system", caller="human", depth=0, step_type="run_finished",
                detail={"status": "failed", "cash_at_end": read_cash()},
            )
            raise

    trail.record(
        agent="system", caller="human", depth=0, step_type="run_finished",
        detail={
            "status": "completed",
            "cash_at_end": read_cash(),
            "delegations_used": deps.delegations_used[0],
            "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Restore the working database from the original before running.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_working_database()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"RUN-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    print(f"run_id: {run_id}")
    print(f"model : {MODEL_NAME} via Portkey")
    print(f"db    : {WORKING_DB.name}")
    print(f"audit : {AUDIT_PATH.name} (appended, never wiped)\n")

    report = asyncio.run(run_shift(run_id))

    if report is not None:
        print("\n--- shift report ---")
        print(json.dumps(report.model_dump(), indent=2))
        report_path = OUTPUT_DIR / "shift_report.json"
        report_path.write_text(json.dumps(report.model_dump(), indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {report_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
