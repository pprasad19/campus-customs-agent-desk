/** Thin typed wrapper over the Campus Customs backend. */

import type {
  ApproveResponse,
  CashResponse,
  EventsResponse,
  RunResponse,
  TicketsResponse,
} from "./types";

export const API_BASE = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* the body was not JSON; the status line is all we have */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const api = {
  tickets: () => request<TicketsResponse>("/tickets"),

  cash: () => request<CashResponse>("/cash"),

  events: (limit = 400, runId?: string) =>
    request<EventsResponse>(
      `/events?limit=${limit}${runId ? `&run_id=${encodeURIComponent(runId)}` : ""}`,
    ),

  runTicket: (ticketId: number) =>
    request<RunResponse>(`/tickets/${ticketId}/run`, { method: "POST" }),

  approve: (approvalId: string, approvedBy: string, note?: string) =>
    request<ApproveResponse>(`/approvals/${approvalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy, note: note ?? null }),
    }),

  reject: (approvalId: string, rejectedBy: string, note?: string) =>
    request<{ approval_id: string; status: string }>(
      `/approvals/${approvalId}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ rejected_by: rejectedBy, note: note ?? null }),
      },
    ),

  reset: () =>
    request<{ reset: boolean; balance: number; open_tickets: number }>("/reset", {
      method: "POST",
    }),
};
