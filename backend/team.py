"""The Campus Customs agent team.

Five Pydantic AI agents — Boss, Inventory, Accounting, Facilities and Customer
Service — all running gpt-6-luna through Portkey, all sharing one MCP toolset.

Connectivity is complete: every agent can delegate to every other agent through
an `ask_<role>` tool, including a specialist escalating back to the Boss. The
mesh is bounded by three limits so it cannot spin:

  * depth      — a delegation chain stops at MAX_DELEGATION_DEPTH
  * budget     — the team shares MAX_DELEGATIONS_PER_RUN across the whole run
  * usage      — token and request ceilings from TEAM_USAGE_LIMITS

Shop facts come only from the MCP server. There is no second tools layer here
that reaches past it into SQLite.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset

from .audit import AuditTrail, usage_dict
from .config import (
    MAX_DELEGATION_DEPTH,
    MCP_CONFIG_PATH,
    MCP_INIT_TIMEOUT_SECONDS,
    MCP_READ_TIMEOUT_SECONDS,
    MODEL_SETTINGS,
    PROJECT_ROOT,
    TEAM_USAGE_LIMITS,
    build_model,
    load_prompt,
)
from .models import ROLES, Role, ShiftReport, SpecialistFinding, TeamDeps


def _resolve(value: str) -> str:
    """Make a path from .mcp.json absolute, relative to the project root."""
    path = Path(value)
    if path.is_absolute():
        return value
    candidate = PROJECT_ROOT / path
    return str(candidate) if candidate.exists() else value


def load_shop_toolsets() -> list[Any]:
    """Build the MCP toolsets described by .mcp.json.

    .mcp.json holds relative paths on purpose, so the project stays portable
    and the file is still valid for other MCP clients. Those paths are relative
    to the Homework 5 folder, but this process is almost never launched from
    there — uvicorn is started from backend/, and a reloader may run from
    somewhere else again. Resolving against the project root here, rather than
    trusting the working directory, is what stops the server spawn failing with
    "the system cannot find the file specified".
    """
    config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    toolsets: list[Any] = []

    for name, server in config.get("mcpServers", {}).items():
        if "command" not in server:
            raise ValueError(f"MCP server {name!r} in .mcp.json has no command.")

        # The child needs the real environment as well as the shop variables;
        # on Windows a bare env would strip PATH and SystemRoot.
        env = {**os.environ, **(server.get("env") or {})}

        transport = StdioTransport(
            command=_resolve(server["command"]),
            args=[_resolve(a) for a in (server.get("args") or [])],
            env=env,
            # Anchor the child here too, so any relative path it is handed
            # resolves the same way no matter who launched the parent.
            cwd=str(PROJECT_ROOT),
            # Keep the process between connections rather than paying the
            # start-up cost again for every agent that reaches for a tool.
            keep_alive=True,
        )
        toolsets.append(
            MCPToolset(
                transport,
                id=name,
                # The server needs about five seconds just to import its
                # dependencies before it can answer `initialize`, and that is on
                # an idle machine. During a run the box is also carrying uvicorn,
                # the Vite dev server and the model calls, so the handshake can
                # take considerably longer. Without a generous window here the
                # connection is abandoned mid-start and the run dies with
                # "Failed to initialize server session".
                init_timeout=MCP_INIT_TIMEOUT_SECONDS,
                read_timeout=MCP_READ_TIMEOUT_SECONDS,
            ).prefixed(name)
        )

    if not toolsets:
        raise ValueError(f"No MCP servers defined in {MCP_CONFIG_PATH}.")
    return toolsets

# What each specialist is for, used in the delegation tool descriptions the
# model actually sees.
ROLE_BLURB: dict[str, str] = {
    "boss": (
        "the shop lead who owns the final decision on a ticket and can weigh one "
        "ticket against another"
    ),
    "inventory": (
        "stock levels per SKU and size, vendor choice, lead times, and whether a "
        "vendor is able to ship"
    ),
    "accounting": (
        "cash balance, invoices, affordability, payment approval requests, and "
        "executing approved payments"
    ),
    "facilities": "the lease, rent owed, the due date, and the landlord",
    "customer_service": (
        "anything a customer will read, and judging discount or price-override "
        "requests against unit cost"
    ),
}


def build_team(trail: AuditTrail) -> dict[Role, Agent]:
    """Create the five agents and wire every delegation edge between them.

    The same toolset objects are handed to all five agents, so there is exactly
    one MCP connection behind the team rather than one per agent.
    """
    model = build_model()
    toolsets = load_shop_toolsets()

    agents: dict[Role, Agent] = {}

    for role in ROLES:
        # The Boss produces the shift report; specialists produce findings.
        output_type: Any = ShiftReport if role == "boss" else SpecialistFinding
        agents[role] = Agent(
            model,
            output_type=output_type,
            instructions=load_prompt(role),
            deps_type=TeamDeps,
            toolsets=toolsets,
            model_settings=MODEL_SETTINGS,
            name=role,
            retries=2,
        )

    _wire_delegation(agents, trail)
    return agents


def _wire_delegation(agents: dict[Role, Agent], trail: AuditTrail) -> None:
    """Give every agent an `ask_<other>` tool for all four of the others."""
    for caller_role in ROLES:
        for target_role in ROLES:
            if caller_role == target_role:
                continue
            tool = _make_delegation_tool(agents, trail, caller_role, target_role)
            agents[caller_role].tool(
                tool,
                name=f"ask_{target_role}",
                description=(
                    f"Ask the {target_role.replace('_', ' ')} agent a single specific "
                    f"question. They own {ROLE_BLURB[target_role]}. Include the ticket "
                    "id and any figures you already have so they do not look them up "
                    "again. Costs a full model round trip, so do not use it for a "
                    "lookup you could make yourself."
                ),
            )


def _render_reply(target_role: str, output: Any) -> str:
    """Flatten whatever an agent returned into a few readable lines.

    Connectivity is complete, which means a specialist can escalate to the Boss
    — and the Boss answers with a ShiftReport, not a SpecialistFinding. Both
    shapes have to be handled here; assuming a SpecialistFinding is what made
    `ask_boss` fail with "'ShiftReport' object has no attribute 'summary'".
    """
    if isinstance(output, ShiftReport):
        lines = [
            f"{target_role} says: shift position on {output.shop_date} — "
            f"cash ${output.cash_at_start:,.2f} at the start, "
            f"${output.cash_at_end:,.2f} now, ${output.total_paid_out:,.2f} paid out."
        ]
        for ticket in output.tickets:
            lines.append(
                f"Ticket {ticket.ticket_id}: {ticket.outcome} — {ticket.what_was_done} "
                f"(because {ticket.why})"
            )
        if output.outstanding_for_human:
            lines.append("Left for a human: " + "; ".join(output.outstanding_for_human))
        if output.notes:
            lines.append(f"Note: {output.notes}")
        return "\n".join(lines)

    if isinstance(output, SpecialistFinding):
        lines = [f"{target_role} says: {output.summary}"]
        if output.facts_from_mcp:
            lines.append("Facts: " + "; ".join(output.facts_from_mcp))
        lines.append(f"Recommendation: {output.recommendation}")
        if output.blockers:
            lines.append("Blockers: " + "; ".join(output.blockers))
        if output.needs_human_approval:
            lines.append("This needs a human to approve before money moves.")
        if output.actions_taken:
            lines.append("Actions taken: " + "; ".join(output.actions_taken))
        return "\n".join(lines)

    # Nothing else should reach here, but a delegation must not crash the run.
    return f"{target_role} says: {output}"


def _make_delegation_tool(
    agents: dict[Role, Agent], trail: AuditTrail, caller_role: str, target_role: str
):
    """Build one delegation edge, caller -> target, with its limits and audit."""

    async def ask(ctx: RunContext[TeamDeps], question: str) -> str:
        deps = ctx.deps

        # Limit 1: how deep a chain of delegations may go.
        if deps.depth >= deps.max_depth:
            refusal = (
                f"Delegation refused: {caller_role} is already {deps.depth} levels deep "
                f"and the limit is {deps.max_depth}. Answer this yourself with direct "
                "tool calls, or hand it back to whoever asked you."
            )
            trail.record(
                agent=caller_role, caller=deps.caller, depth=deps.depth,
                step_type="refusal",
                detail={"refused": "delegation", "to": target_role, "reason": refusal},
            )
            return refusal

        # Limit 2: a shared budget so five agents cannot collectively loop.
        if not deps.spend_delegation():
            refusal = (
                f"Delegation refused: the team has used all {deps.delegation_budget} "
                "delegations for this run. Finish with direct tool calls and say in "
                "your answer that the delegation budget ran out."
            )
            trail.record(
                agent=caller_role, caller=deps.caller, depth=deps.depth,
                step_type="refusal",
                detail={"refused": "delegation", "to": target_role, "reason": refusal},
            )
            return refusal

        trail.record(
            agent=caller_role, caller=deps.caller, depth=deps.depth,
            step_type="delegation",
            detail={
                "from": caller_role,
                "to": target_role,
                "question": question,
                "delegations_used": deps.delegations_used[0],
                "delegation_budget": deps.delegation_budget,
            },
        )

        child_deps = deps.child(caller=caller_role)
        # usage=ctx.usage makes the child's tokens count against the same
        # team-wide ceiling as the parent's, so the budget is genuinely shared.
        # The child shares the parent's usage counter, so its tokens count
        # against the same team-wide ceiling. It therefore has to carry the same
        # limits object too; a smaller one would be measured against the whole
        # team's usage and would stop the run early.
        result = await agents[target_role].run(
            question,
            deps=child_deps,
            usage=ctx.usage,
            usage_limits=TEAM_USAGE_LIMITS,
            # Stream this specialist's steps onto the board while it works,
            # rather than dumping them when it returns.
            event_stream_handler=trail.live_handler(
                agent=target_role, caller=caller_role, depth=child_deps.depth
            ),
        )

        trail.record_agent_messages(
            agent=target_role, caller=caller_role, depth=child_deps.depth,
            messages=result.new_messages(),
        )
        output = result.output
        trail.record(
            agent=target_role, caller=caller_role, depth=child_deps.depth,
            step_type="agent_finished",
            detail={"finding": output.model_dump()},
            usage=usage_dict(result.usage),
        )

        # Hand back a compact rendering rather than the raw object, so the
        # calling model sees the facts without a wall of JSON.
        return _render_reply(target_role, output)

    ask.__name__ = f"ask_{target_role}"
    return ask


__all__ = ["build_team", "MAX_DELEGATION_DEPTH"]
