/** Who the five agents are, and how each one reads on the desk.

Every agent gets its own ink colour, monogram and desk-plate title, so a glance
at the floor tells you who is speaking without reading a word.
*/

import type { AgentActivity, AuditStep } from "./types";

export interface AgentIdentity {
  role: string;
  name: string;
  title: string;
  monogram: string;
  /** Ink colour, used for the plate, the rail and the speech marks. */
  ink: string;
  /** A soft wash of the same hue, for backgrounds. */
  wash: string;
  owns: string;
}

export const AGENTS: AgentIdentity[] = [
  {
    role: "boss",
    name: "The Boss",
    title: "Shop lead",
    monogram: "B",
    ink: "#f0a93b",
    wash: "#3a2a12",
    owns: "Runs the shift and owns the final call",
  },
  {
    role: "inventory",
    name: "Inventory",
    title: "Stock & vendors",
    monogram: "I",
    ink: "#3ddc9a",
    wash: "#102e24",
    owns: "Counts the shelf, picks the supplier",
  },
  {
    role: "accounting",
    name: "Accounting",
    title: "Cash & invoices",
    monogram: "A",
    ink: "#ff6b81",
    wash: "#331620",
    owns: "Guards the money, prepares payments",
  },
  {
    role: "facilities",
    name: "Facilities",
    title: "Lease & rent",
    monogram: "F",
    ink: "#a98bff",
    wash: "#241d44",
    owns: "Knows the lease and the landlord",
  },
  {
    role: "customer_service",
    name: "Customer Service",
    title: "Customers & pricing",
    monogram: "C",
    ink: "#4f9dff",
    wash: "#122740",
    owns: "Writes to people, judges discounts",
  },
];

export const SYSTEM_IDENTITY: AgentIdentity = {
  role: "system",
  name: "The Desk",
  title: "Run log",
  monogram: "·",
  ink: "#8c97b8",
  wash: "#1e2540",
  owns: "Opens and closes the shift",
};

export function identityFor(role: string): AgentIdentity {
  return AGENTS.find((a) => a.role === role) ?? SYSTEM_IDENTITY;
}


interface ShiftReportish {
  shop_date?: string;
  tickets?: Array<{
    ticket_id: number;
    outcome: string;
    what_was_done: string;
    why: string;
    money_moved?: number;
    approval_ids?: string[];
    draft_ids?: string[];
  }>;
  cash_at_start?: number;
  cash_at_end?: number;
  total_paid_out?: number;
  outstanding_for_human?: string[];
  notes?: string;
}

const OUTCOME_WORD: Record<string, string> = {
  resolved: "resolved it",
  waiting_on_approval: "left it waiting on a signature",
  waiting_on_vendor: "left it waiting on a vendor",
  refused: "refused it",
  needs_human_decision: "left it for a person to decide",
};

/** Render the Boss's shift report in the same shape a specialist answer uses. */
function reportToFinding(report: ShiftReportish): AgentActivity["finding"] {
  const tickets = report.tickets ?? [];
  const summary = tickets.length
    ? tickets
        .map(
          (t) =>
            `Ticket ${t.ticket_id}: ${OUTCOME_WORD[t.outcome] ?? t.outcome}. ${t.what_was_done}`,
        )
        .join(" ")
    : "Closed the shift with nothing to change.";

  const facts: string[] = [];
  if (report.cash_at_start !== undefined && report.cash_at_end !== undefined) {
    facts.push(
      `cash: $${report.cash_at_start.toFixed(2)} at the start, ` +
        `$${report.cash_at_end.toFixed(2)} at the end`,
    );
  }
  if (report.total_paid_out) facts.push(`paid out: $${report.total_paid_out.toFixed(2)}`);
  for (const t of tickets) if (t.why) facts.push(`ticket ${t.ticket_id}: ${t.why}`);

  const actions: string[] = [];
  for (const t of tickets) {
    for (const a of t.approval_ids ?? []) actions.push(`raised ${a}`);
    for (const d of t.draft_ids ?? []) actions.push(`drafted ${d}`);
    if (t.money_moved) actions.push(`paid $${t.money_moved.toFixed(2)}`);
  }

  const outstanding = report.outstanding_for_human ?? [];
  return {
    summary,
    recommendation: outstanding.length ? outstanding.join(" ") : (report.notes || "Nothing further."),
    blockers: [],
    facts_from_mcp: facts,
    needs_human_approval: outstanding.length > 0,
    actions_taken: actions,
  };
}

/** Turn a flat list of audit steps into one activity record per agent. */
export function summariseByAgent(steps: AuditStep[]): AgentActivity[] {
  const byRole = new Map<string, AuditStep[]>();
  for (const step of steps) {
    if (step.agent === "system") continue;
    const list = byRole.get(step.agent) ?? [];
    list.push(step);
    byRole.set(step.agent, list);
  }

  // Work out which delegations are still outstanding.
  //
  // A delegated agent writes nothing to the audit trail until it has finished —
  // its whole message history is recorded in one go when it returns. So while
  // Inventory is working, the only evidence is the Boss's `delegation` step. If
  // we only trusted steps, Inventory would say "not called on this ticket" at
  // exactly the moment it is busiest, and the Boss would look like the only one
  // doing anything.
  const outstanding: { from: string; to: string }[] = [];
  for (const step of steps) {
    if (step.step_type === "delegation") {
      outstanding.push({
        from: String(step.detail.from ?? step.agent),
        to: String(step.detail.to ?? ""),
      });
    } else if (step.step_type === "agent_finished") {
      const i = outstanding.findIndex((d) => d.to === step.agent && d.from === step.caller);
      if (i >= 0) outstanding.splice(i, 1);
    }
  }
  const beingAsked = new Set(outstanding.map((d) => d.to));
  const waitingFor = new Map(outstanding.map((d) => [d.from, d.to]));

  // An agent that has been called but has not reported yet still belongs on the
  // floor, even with no steps of its own to show.
  for (const role of beingAsked) {
    if (!byRole.has(role)) byRole.set(role, []);
  }

  const lastSeq = steps.length ? steps[steps.length - 1].seq : 0;

  return AGENTS.filter((a) => byRole.has(a.role)).map((identity) => {
    const agentSteps = byRole.get(identity.role)!;
    const tools = agentSteps
      .filter((s) => s.step_type === "tool_call")
      .map((s) => String(s.detail.tool_name ?? "").replace(/^campus-customs_/, ""))
      // `final_result` is how pydantic-ai collects an agent's structured
      // answer, not something the shop can do, and `ask_*` is a handoff that
      // gets its own chip. Neither belongs in the list of shop tools used.
      .filter((t) => t && t !== "final_result" && !t.startsWith("ask_"));

    const spoke = agentSteps
      .filter((s) => s.step_type === "model_response" && typeof s.detail.text === "string")
      .map((s) => s.detail.text as string);

    const finished = [...agentSteps].reverse().find((s) => s.step_type === "agent_finished");

    // Specialists finish with a SpecialistFinding; the Boss finishes with a
    // ShiftReport, which has none of the same fields. Both have to be turned
    // into something the card can show, or the Boss sits on "working" forever
    // even though the run is over.
    const finding: AgentActivity["finding"] =
      (finished?.detail.finding as AgentActivity["finding"]) ??
      (finished?.detail.shift_report
        ? reportToFinding(finished.detail.shift_report as ShiftReportish)
        : null);

    const delegated = agentSteps
      .filter((s) => s.step_type === "delegation")
      .map((s) => String(s.detail.to ?? ""))
      .filter(Boolean);

    const last = agentSteps.length ? agentSteps[agentSteps.length - 1] : null;
    const waitingOn = waitingFor.get(identity.role);

    return {
      role: identity.role,
      steps: agentSteps,
      toolsUsed: Array.from(new Set(tools)),
      toolCallCount: tools.length,
      saidLast: spoke.length ? spoke[spoke.length - 1] : null,
      finding: finding ?? null,
      delegatedTo: Array.from(new Set(delegated)),
      waitingOn,
      // Busy means one of three things: called and not yet back, blocked on
      // somebody else's answer, or holding the most recent step with no report
      // filed. All three are work in progress.
      active:
        beingAsked.has(identity.role) ||
        waitingOn !== undefined ||
        (last !== null && last.seq === lastSeq && !finished),
    };
  });
}

/** A short human label for one audit step. */
export function describeStep(step: AuditStep): { label: string; body: string } {
  const d = step.detail;
  switch (step.step_type) {
    case "run_started":
      return { label: "Shift opened", body: `Working ${d.scope ?? "the board"} on ${d.shop_date}.` };
    case "run_finished":
      return { label: "Shift closed", body: `Closing balance $${Number(d.cash_at_end ?? 0).toFixed(2)}.` };
    case "agent_started":
      return { label: "Picked up", body: String(d.prompt_received ?? "") };
    case "model_response":
      return { label: "Said", body: String(d.text ?? d.thinking ?? "") };
    case "tool_call":
      return {
        label: "Used",
        body: `${String(d.tool_name ?? "").replace(/^campus-customs_/, "")}(${formatArgs(d.tool_args)})`,
      };
    case "tool_result":
      return {
        label: "Got back",
        body: summariseResult(d.result),
      };
    case "delegation":
      return { label: `Asked ${String(d.to ?? "")}`, body: String(d.question ?? "") };
    case "refusal":
      return { label: "Refused", body: String(d.reason ?? d.retry_reason ?? "") };
    case "agent_finished":
      return {
        label: "Reported",
        body: String(
          (d.finding as Record<string, unknown>)?.summary ??
            (d.shift_report as Record<string, unknown>)?.notes ??
            "Finished.",
        ),
      };
    case "error":
      return { label: "Error", body: `${d.exception}: ${d.message}` };
    default:
      return { label: step.step_type, body: "" };
  }
}

function formatArgs(args: unknown): string {
  if (!args || typeof args !== "object") return "";
  return Object.entries(args as Record<string, unknown>)
    .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v}"` : v}`)
    .join(", ");
}

function summariseResult(result: unknown): string {
  if (result == null) return "";
  if (typeof result !== "object") return String(result);
  const r = result as Record<string, unknown>;
  // Pull out the handful of fields that actually matter at a glance.
  const interesting = [
    "qty", "balance", "monthly_rent", "unit_cost", "list_price", "can_ship",
    "days_until_due", "is_overdue", "amount", "status", "approval_id", "paid",
    "draft_id", "count", "open_count", "refused", "reason",
  ];
  const picked = interesting
    .filter((k) => k in r)
    .map((k) => `${k}: ${JSON.stringify(r[k])}`);
  if (picked.length) return picked.join("  ·  ");
  return JSON.stringify(r).slice(0, 180);
}
