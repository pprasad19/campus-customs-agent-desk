"""Data types for the Campus Customs agent team.

Three groups live here:
  * run plumbing the agents carry around (TeamDeps)
  * structured outputs the agents must produce (SpecialistFinding, ShiftReport)
  * the audit record shape written to output/audit_trail.json (AuditStep)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------

Role = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

ROLES: tuple[Role, ...] = (
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
)

TicketOutcome = Literal[
    "resolved",
    "waiting_on_approval",
    "waiting_on_vendor",
    "refused",
    "needs_human_decision",
]


# --------------------------------------------------------------------------
# Run plumbing
# --------------------------------------------------------------------------


@dataclass
class TeamDeps:
    """Carried through every agent run, including delegated ones.

    depth exists to stop the team talking in circles. Every delegation makes a
    child with depth + 1, and the delegation tool refuses once max_depth is
    reached, so a loop of agents asking each other questions terminates instead
    of burning the token budget.
    """

    run_id: str
    shop_date: str
    depth: int = 0
    caller: str = "human"
    max_depth: int = 3
    delegation_budget: int = 12
    delegations_used: list[int] = field(default_factory=lambda: [0])

    def child(self, caller: str) -> "TeamDeps":
        return TeamDeps(
            run_id=self.run_id,
            shop_date=self.shop_date,
            depth=self.depth + 1,
            caller=caller,
            max_depth=self.max_depth,
            delegation_budget=self.delegation_budget,
            delegations_used=self.delegations_used,
        )

    def spend_delegation(self) -> bool:
        """Claim one delegation from the shared team-wide budget."""
        if self.delegations_used[0] >= self.delegation_budget:
            return False
        self.delegations_used[0] += 1
        return True


# --------------------------------------------------------------------------
# Agent outputs
# --------------------------------------------------------------------------


class SpecialistFinding(BaseModel):
    """What a specialist hands back to whoever asked it."""

    summary: str = Field(description="Two or three sentences answering the question asked.")
    facts_from_mcp: list[str] = Field(
        default_factory=list,
        description=(
            "Each concrete fact used, with the number and the tool it came from, "
            "e.g. 'check_inventory_stock: CC-TEE-WHITE/S qty=0'."
        ),
    )
    recommendation: str = Field(description="What should happen next, stated plainly.")
    blockers: list[str] = Field(
        default_factory=list,
        description="Anything preventing this from being done now.",
    )
    needs_human_approval: bool = Field(
        default=False,
        description="True if acting on this would move money and so needs a person.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Write tools actually called, if any. Empty when nothing changed.",
    )


class TicketResolution(BaseModel):
    """The Boss's verdict on one ticket."""

    ticket_id: int
    outcome: TicketOutcome
    what_was_done: str = Field(description="Plain account of the actions taken on this ticket.")
    why: str = Field(description="The reasoning, naming the shop rule or number that decided it.")
    money_moved: float = Field(default=0.0, description="Cash actually paid out for this ticket.")
    approval_ids: list[str] = Field(default_factory=list)
    draft_ids: list[str] = Field(default_factory=list)
    specialists_consulted: list[str] = Field(default_factory=list)


class ShiftReport(BaseModel):
    """The Boss's end-of-run report for the whole shift."""

    shop_date: str = Field(description="From get_shop_date, not the real calendar.")
    tickets: list[TicketResolution]
    cash_at_start: float
    cash_at_end: float
    total_paid_out: float = Field(default=0.0)
    outstanding_for_human: list[str] = Field(
        default_factory=list,
        description="Anything a person must decide or send before the shop is square.",
    )
    notes: str = Field(default="", description="Anything else worth telling the owner.")


# --------------------------------------------------------------------------
# Audit record
# --------------------------------------------------------------------------


class AuditStep(BaseModel):
    """One auditable step. Appended to output/audit_trail.json, never replaced."""

    run_id: str
    seq: int = Field(description="Order within the run, starting at 1.")
    recorded_at_utc: str = Field(description="Real wall-clock time this line was written.")
    shop_date: str = Field(description="The shop's own date, from desk.date_today.")
    agent: str = Field(description="Which of the five roles this step belongs to.")
    caller: str = Field(description="Who asked this agent to act.")
    depth: int = Field(description="Delegation depth; 0 is the top-level run.")
    step_type: str = Field(
        description=(
            "run_started | agent_started | model_response | tool_call | tool_result | "
            "delegation | agent_finished | refusal | run_finished | error"
        )
    )
    detail: dict[str, Any] = Field(
        default_factory=dict, description="Step payload: prompts, tool args, returns."
    )
    usage: dict[str, Any] = Field(
        default_factory=dict, description="Token and request counts where known."
    )
