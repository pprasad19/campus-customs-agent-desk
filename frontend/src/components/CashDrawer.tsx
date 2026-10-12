import { useEffect, useRef, useState } from "react";
import type { ApproveResponse, CashResponse } from "../types";
import { AllClearArt, CheckIcon, CoinsIcon, PenIcon, TagIcon, WarnIcon } from "./Icons";

interface Props {
  cash: CashResponse | null;
  running: boolean;
  /** The ticket currently selected, so the signature can be cleared per ticket. */
  ticketId: number | null;
  onApprove: (approvalId: string, who: string) => Promise<ApproveResponse>;
  onReject: (approvalId: string, who: string) => Promise<void>;
}

/** Counts the balance down rather than snapping, so a payment is felt. */
function useRolling(target: number | undefined) {
  const [shown, setShown] = useState(target ?? 0);
  const [dropping, setDropping] = useState(false);
  const previous = useRef(target ?? 0);

  useEffect(() => {
    if (target === undefined) return;
    const from = previous.current;
    if (from === target) return;
    previous.current = target;
    setDropping(target < from);

    const startedAt = performance.now();
    const span = 850;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - startedAt) / span);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(from + (target - from) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else setTimeout(() => setDropping(false), 700);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return { shown, dropping };
}

export function CashDrawer({ cash, running, ticketId, onApprove, onReject }: Props) {
  const { shown, dropping } = useRolling(cash?.balance);
  const [who, setWho] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<{ ok: boolean; text: string } | null>(null);

  // A signature is given for one decision, not left lying on the desk. Moving
  // to another ticket clears the name and the previous outcome message, so
  // nobody approves a second payment on the strength of a name they typed for
  // something else.
  useEffect(() => {
    setWho("");
    setOutcome(null);
  }, [ticketId]);

  // Nothing is offered for signature while the team is still working.
  //
  // An agent raises an approval the moment it decides one is needed, which can
  // be a minute before the run ends. Showing it straight away invites a
  // signature on a half-finished picture — the Boss may still be weighing this
  // payment against another ticket's claim on the same balance. The queue is
  // revealed once the run is over and the reasoning is complete.
  const pending = running ? [] : (cash?.pending_approvals ?? []);
  const hiddenWhileRunning = running ? (cash?.pending_approvals?.length ?? 0) : 0;

  const act = async (id: string, approve: boolean) => {
    if (!who.trim()) {
      setOutcome({ ok: false, text: "Sign your name first — an approval has to name a person." });
      return;
    }
    setBusy(id);
    setOutcome(null);
    try {
      if (approve) {
        const r = await onApprove(id, who.trim());
        if (r.paid) {
          setOutcome({ ok: true, text: `Paid. Balance now $${r.balance_after.toFixed(2)}.` });
        } else if (r.decision_applied) {
          setOutcome({
            ok: true,
            text:
              `Price agreed at $${(r.agreed_unit_price ?? 0).toFixed(2)} per unit on ` +
              `ticket #${r.ticket_id}. No cash moved.`,
          });
        } else {
          setOutcome({ ok: false, text: r.refused_reason ?? "The shop refused that." });
        }
      } else {
        await onReject(id, who.trim());
        setOutcome({ ok: true, text: "Turned down. No money moved." });
      }
    } catch (e) {
      setOutcome({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <aside className="drawer">
      <div className={`till ${dropping ? "dropping" : ""}`}>
        <span className="till-label"><CoinsIcon size={14} /> Checking</span>
        <div className="till-amount">
          <span className="cur">$</span>
          {shown.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </div>
        <div className="till-meta">
          {cash ? (
            <>
              <span>{cash.payments_made} paid out</span>
              <span className="dot">•</span>
              <span>${cash.total_paid_out.toFixed(2)} total</span>
            </>
          ) : (
            <span>—</span>
          )}
        </div>
        {cash && !running && cash.pending_approval_total > 0 && (
          <div className="till-pending">
            ${cash.pending_approval_total.toFixed(2)} awaiting your signature
            <span className="would-leave">
              would leave ${cash.balance_if_all_pending_paid.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      <div className="signature">
        <label htmlFor="who"><PenIcon size={13} /> Signed by</label>
        <input
          id="who"
          value={who}
          placeholder="your name"
          onChange={(e) => setWho(e.target.value)}
          autoComplete="name"
        />
        <p className="sig-note">
          The agents can prepare a payment. Only a signature here moves money.
        </p>
      </div>

      <div className="slips-head">
        <h2>To sign</h2>
        {!!pending.length && <span className="count warm">{pending.length}</span>}
      </div>

      {!pending.length && (
        <div className="nothing-to-sign">
          {running ? (
            <>
              <span className="spinner" aria-hidden />
              <span>
                The team is still working.
                {hiddenWhileRunning > 0
                  ? ` ${hiddenWhileRunning} item${hiddenWhileRunning > 1 ? "s" : ""} will come here once the run finishes.`
                  : " Anything needing your signature will appear when the run finishes."}
              </span>
            </>
          ) : (
            <>
              <AllClearArt width={118} />
              <span>Nothing waiting on you.</span>
            </>
          )}
        </div>
      )}

      {pending.map((a) => {
        const isDecision = a.category === "decision";

        // A price override is not a payment. It gets its own slip: the terms
        // being agreed, the margin they leave, and no claim on the balance.
        if (isDecision) {
          const thin = (a.margin_per_unit ?? 0) <= 0;
          return (
            <article key={a.approval_id} className={`cheque decision ${thin ? "risky" : ""}`}>
              <div className="cheque-head">
                <span className="kind"><TagIcon size={13} /> Price call · ticket #{a.ticket_id}</span>
                <span className="amount">${(a.proposed_unit_price ?? 0).toFixed(2)}</span>
              </div>

              <div className="terms">
                {a.qty} × <code>{a.sku}</code> size {a.size} at
                {" "}${(a.proposed_unit_price ?? 0).toFixed(2)} each
                <span className="off">
                  {(a.discount_percent ?? 0).toFixed(0)}% off the ${(a.list_price ?? 0).toFixed(2)} list
                </span>
              </div>

              <p className="because">{a.reason}</p>

              <dl className="maths">
                <div><dt>Cost each</dt><dd>${(a.unit_cost ?? 0).toFixed(2)}</dd></div>
                <div><dt>Margin each</dt>
                  <dd className={thin ? "neg" : ""}>${(a.margin_per_unit ?? 0).toFixed(2)}</dd></div>
                <div><dt>Order total</dt><dd>${(a.total_at_proposed ?? 0).toFixed(2)}</dd></div>
                <div><dt>Total margin</dt>
                  <dd className={thin ? "neg" : ""}>${(a.total_margin ?? 0).toFixed(2)}</dd></div>
              </dl>

              <div className="cheque-meta">
                <span>asked by <b>{a.requested_by}</b></span>
                <span className="dot">•</span>
                <span>{a.requested_on_shop_date}</span>
              </div>

              {a.below_cost && (
                <div className="after bad">
                  <WarnIcon size={14} />
                  Below the ${(a.unit_cost ?? 0).toFixed(2)} unit cost — every unit sells at a loss.
                </div>
              )}
              {!a.below_cost && !a.can_supply_in_full && (
                <div className="after warn">
                  Only {a.qty_on_hand} on hand, short by {a.short_by}. Approving agrees the
                  price; the shortfall still needs sourcing.
                </div>
              )}
              {!a.below_cost && a.can_supply_in_full && (
                <div className="after">
                  <CheckIcon size={14} />
                  No cash moves. Stock covers all {a.qty} units.
                </div>
              )}

              <div className="cheque-actions">
                <button
                  className="approve"
                  disabled={busy === a.approval_id}
                  onClick={() => act(a.approval_id, true)}
                >
                  {busy === a.approval_id ? "…" : "Approve price"}
                </button>
                <button
                  className="decline"
                  disabled={busy === a.approval_id}
                  onClick={() => act(a.approval_id, false)}
                >
                  Decline
                </button>
              </div>

              <span className="cheque-id">{a.approval_id}</span>
            </article>
          );
        }

        const amount = a.amount ?? 0;
        const after = (cash?.balance ?? 0) - amount;
        const overdraws = after < 0;
        return (
          <article key={a.approval_id} className={`cheque ${overdraws ? "risky" : ""}`}>
            <div className="cheque-head">
              <span className="kind">{a.kind === "rent" ? "Rent" : "Invoice"} #{a.ref_id}</span>
              <span className="amount">${amount.toFixed(2)}</span>
            </div>

            <p className="because">{a.reason}</p>

            <div className="cheque-meta">
              <span>asked by <b>{a.requested_by}</b></span>
              <span className="dot">•</span>
              <span>{a.requested_on_shop_date}</span>
            </div>

            <div className={`after ${overdraws ? "bad" : ""}`}>
              {overdraws ? (
                <>Would overdraw by ${Math.abs(after).toFixed(2)} — the shop will refuse this.</>
              ) : (
                <>Leaves ${after.toFixed(2)} in checking.</>
              )}
            </div>

            <div className="cheque-actions">
              <button
                className="approve"
                disabled={busy === a.approval_id}
                onClick={() => act(a.approval_id, true)}
              >
                {busy === a.approval_id ? "…" : "Approve & pay"}
              </button>
              <button
                className="decline"
                disabled={busy === a.approval_id}
                onClick={() => act(a.approval_id, false)}
              >
                Decline
              </button>
            </div>

            <span className="cheque-id">{a.approval_id}</span>
          </article>
        );
      })}

      {outcome && (
        <div className={`outcome ${outcome.ok ? "good" : "bad"}`}>{outcome.text}</div>
      )}
    </aside>
  );
}
