import { identityFor } from "../agents";
import { LedgerArt } from "./Icons";
import type { ShiftReport } from "../types";

const OUTCOME_LABEL: Record<string, string> = {
  resolved: "Resolved",
  waiting_on_approval: "Waiting on a signature",
  waiting_on_vendor: "Waiting on a vendor",
  refused: "Refused",
  needs_human_decision: "Needs your decision",
};

export function ShiftReportCard({ report }: { report: ShiftReport }) {
  const moved = report.cash_at_start - report.cash_at_end;

  return (
    <section className="report">
      <div className="report-head">
        <span className="ledger-mark" aria-hidden><LedgerArt width={44} /></span>
        <h2>Closing note</h2>
        <span className="date">{report.shop_date}</span>
      </div>

      <div className="ledger">
        <div>
          <span className="k">Opened with</span>
          <b>${report.cash_at_start.toFixed(2)}</b>
        </div>
        <div className="arrow" aria-hidden>→</div>
        <div>
          <span className="k">Closed with</span>
          <b>${report.cash_at_end.toFixed(2)}</b>
        </div>
        <div className={`moved ${moved > 0 ? "out" : "flat"}`}>
          {moved > 0 ? `$${moved.toFixed(2)} went out` : "nothing moved"}
        </div>
      </div>

      {report.tickets.map((t) => (
        <article key={t.ticket_id} className={`verdict v-${t.outcome}`}>
          <header>
            <span className="tno">#{t.ticket_id}</span>
            <span className="out">{OUTCOME_LABEL[t.outcome] ?? t.outcome}</span>
            {t.money_moved > 0 && <span className="paid">${t.money_moved.toFixed(2)}</span>}
          </header>

          <p className="did">{t.what_was_done}</p>
          <p className="why"><span className="why-k">Because</span>{t.why}</p>

          {!!t.specialists_consulted.length && (
            <div className="consulted">
              {t.specialists_consulted.map((s) => {
                const id = identityFor(s);
                return (
                  <span key={s} className="chip" style={{ background: id.wash, color: id.ink }}>
                    {id.monogram} {id.name}
                  </span>
                );
              })}
            </div>
          )}

          {(!!t.approval_ids.length || !!t.draft_ids.length) && (
            <div className="refs">
              {t.approval_ids.map((a) => (
                <span key={a} className="ref">{a}</span>
              ))}
              {t.draft_ids.map((d) => (
                <span key={d} className="ref draft">{d}</span>
              ))}
            </div>
          )}
        </article>
      ))}

      {!!report.outstanding_for_human.length && (
        <div className="for-you">
          <h3>Left for you</h3>
          <ul>
            {report.outstanding_for_human.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      )}

      {report.notes && <p className="notes">{report.notes}</p>}
    </section>
  );
}
