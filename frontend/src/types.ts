/** Shapes returned by the Campus Customs backend. */

export type TicketStatus =
  | "open"
  | "waiting_on_approval"
  | "waiting_on_vendor"
  | "resolved"
  | "refused";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: TicketStatus;
  notes: string | null;
  created_at: string;
  is_open: boolean;
  is_resolved: boolean;
}

export interface TicketsResponse {
  shop_date: string;
  count: number;
  open_count: number;
  tickets: Ticket[];
}

export type Role =
  | "boss"
  | "inventory"
  | "accounting"
  | "facilities"
  | "customer_service"
  | "system";

export interface AuditStep {
  run_id: string;
  seq: number;
  recorded_at_utc: string;
  shop_date: string;
  agent: Role | string;
  caller: string;
  depth: number;
  step_type:
    | "run_started"
    | "agent_started"
    | "model_response"
    | "tool_call"
    | "tool_result"
    | "delegation"
    | "refusal"
    | "agent_finished"
    | "error"
    | "run_finished";
  detail: Record<string, unknown>;
  usage: Record<string, number>;
}

export interface EventsResponse {
  count: number;
  total_steps: number;
  runs: string[];
  latest_run: string | null;
  events: AuditStep[];
}

/** Anything waiting on a person. Two categories share one board:
 *  a "payment" moves cash; a "decision" does not. */
export interface Approval {
  approval_id: string;
  category?: "payment" | "decision";
  status: "pending" | "approved" | "rejected";
  kind: "invoice" | "rent" | "price_override";
  ref_id: number;
  reason: string;
  requested_by: string;
  requested_on_shop_date: string;
  approved_by: string | null;
  decided_on: string | null;
  decision_note: string | null;

  // Payments only.
  amount?: number;
  account?: string;
  balance_at_request?: number;
  affordable_at_request?: boolean;
  consumed_by_payment_id?: number | null;

  // Price-override decisions only.
  ticket_id?: number;
  sku?: string;
  size?: string;
  qty?: number;
  proposed_unit_price?: number;
  unit_cost?: number;
  list_price?: number;
  discount_per_unit?: number;
  discount_percent?: number;
  margin_per_unit?: number;
  total_at_proposed?: number;
  total_at_list?: number;
  total_cost?: number;
  total_margin?: number;
  below_cost?: boolean;
  qty_on_hand?: number;
  short_by?: number;
  can_supply_in_full?: boolean;
  applied_to_ticket?: number | null;
}

export interface CashResponse {
  account: string;
  balance: number;
  as_of_shop_date: string;
  payments_made: number;
  total_paid_out: number;
  pending_approvals: Approval[];
  pending_approval_total: number;
  balance_if_all_pending_paid: number;
}

export interface TicketResolution {
  ticket_id: number;
  outcome: string;
  what_was_done: string;
  why: string;
  money_moved: number;
  approval_ids: string[];
  draft_ids: string[];
  specialists_consulted: string[];
}

export interface ShiftReport {
  shop_date: string;
  tickets: TicketResolution[];
  cash_at_start: number;
  cash_at_end: number;
  total_paid_out: number;
  outstanding_for_human: string[];
  notes: string;
}

export interface RunResponse {
  run_id: string;
  ticket_id: number;
  model: string;
  report: ShiftReport | null;
}

export interface ApproveResponse {
  approval_id: string;
  approved_by: string;
  paid: boolean;
  refused_reason: string | null;
  balance_after: number;
  payment?: Record<string, unknown>;
  decision_applied?: boolean;
  agreed_unit_price?: number;
  total_margin?: number;
  ticket_id?: number;
  note?: string;
}

/** Derived per-agent summary, built in the browser from the audit steps. */
export interface AgentActivity {
  role: string;
  steps: AuditStep[];
  toolsUsed: string[];
  toolCallCount: number;
  saidLast: string | null;
  finding: {
    summary?: string;
    recommendation?: string;
    blockers?: string[];
    facts_from_mcp?: string[];
    needs_human_approval?: boolean;
    actions_taken?: string[];
  } | null;
  delegatedTo: string[];
  /** Currently doing work: either producing steps, or called and not yet back. */
  active: boolean;
  /** Set when this agent has handed out a question and is blocked on the answer. */
  waitingOn?: string;
}
