import { useEffect, useRef, useState } from "react";
import { AGENTS, describeStep, identityFor } from "../agents";
import type { AgentActivity, AuditStep, Ticket } from "../types";
import {
  AgentIcon, AgentPortrait, DeskWatermark, ReceiptEnd, Storefront, TicketHero, ToolIcon,
} from "./Icons";

interface Props {
  activity: AgentActivity[];
  steps: AuditStep[];
  running: boolean;
  runId: string | null;
  ticket: Ticket | null;
  /** True when the floor is showing a finished run loaded from history. */
  pastRun?: boolean;
}

export function AgentFloor({ activity, steps, running, runId, ticket, pastRun }: Props) {
  const [view, setView] = useState<"floor" | "tape">("floor");
  const tapeEnd = useRef<HTMLDivElement | null>(null);

  // Keep the newest line in sight while the team is working.
  useEffect(() => {
    if (view === "tape" && running) {
      tapeEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [steps.length, view, running]);

  const idle = !steps.length && !running;

  return (
    <div className="floor">
      <div className="floor-head">
        <div>
          <h2>The floor</h2>
          <p className="sub">
            {ticket ? (
              <>Ticket <b>#{ticket.id}</b> — {ticket.subject}</>
            ) : (
              "Pick a slip from the spike"
            )}
            {runId ? <span className="runid"> · {runId}</span> : null}
            {pastRun && !running ? <span className="past">last run</span> : null}
          </p>
        </div>

        {running && <span className="working-bar" aria-hidden />}

        <div className="toggle">
          <button
            className={view === "floor" ? "on" : ""}
            onClick={() => setView("floor")}
          >
            Desks
          </button>
          <button
            className={view === "tape" ? "on" : ""}
            onClick={() => setView("tape")}
          >
            Tape {steps.length ? <em>{steps.length}</em> : null}
          </button>
        </div>
      </div>

      {idle && (
        <div className="idle">
          {ticket ? (
            <div className="idle-hero">
              <TicketHero sku={ticket.sku} type={ticket.type} width={150} />
              <div className="idle-hero-text">
                <span className="idle-hero-no">Ticket #{ticket.id}</span>
                <h3>{ticket.subject}</h3>
                <p>
                  {ticket.requester}
                  {ticket.sku ? <> · {ticket.qty} × {ticket.sku}{ticket.size ? ` size ${ticket.size}` : ""}</> : null}
                </p>
              </div>
            </div>
          ) : (
            <div className="idle-art idle-shop" aria-hidden>
              <Storefront width={230} />
            </div>
          )}
          <div className="idle-plates" aria-hidden>
            {AGENTS.map((a) => (
              <span
                key={a.role}
                className="idle-plate"
                style={{ "--plate-ink": a.ink } as React.CSSProperties}
                title={a.name}
              >
                <AgentIcon role={a.role} size={20} />
              </span>
            ))}
          </div>
          <p className="idle-title">Five desks, all quiet.</p>
          <p className="idle-body">
            Choose a slip and ring the bell. Whoever the Boss calls will light up here,
            and you will see every question they ask each other and every tool they touch.
          </p>
        </div>
      )}

      {/* Between runs, show what is currently selected. It keeps the ticket you
          are about to work in front of you while you read a previous run. */}
      {!idle && !running && ticket && (
        <div className="selected-strip">
          <TicketHero sku={ticket.sku} type={ticket.type} width={96} />
          <div className="strip-text">
            <span className="strip-no">Selected · ticket #{ticket.id}</span>
            <b>{ticket.subject}</b>
            <span className="strip-sub">
              {ticket.requester}
              {ticket.sku ? ` · ${ticket.qty} × ${ticket.sku}${ticket.size ? ` size ${ticket.size}` : ""}` : ""}
            </span>
          </div>
          <span className={`strip-status s-${ticket.status}`}>{ticket.status.replace(/_/g, " ")}</span>
        </div>
      )}

      {view === "floor" && !idle && (
        <div className="desks">
          {AGENTS.map((identity) => {
            const a = activity.find((x) => x.role === identity.role);
            const called = Boolean(a);
            return (
              <article
                key={identity.role}
                className={[
                  "desk-card",
                  called ? "called" : "unused",
                  a?.active && running ? "speaking" : "",
                ].join(" ")}
                style={
                  {
                    "--ink": identity.ink,
                    "--wash": identity.wash,
                  } as React.CSSProperties
                }
              >
                <DeskWatermark role={identity.role} />
                <header>
                  <span className="plate"><AgentPortrait role={identity.role} size={38} /></span>
                  <div className="who">
                    <b>{identity.name}</b>
                    <span>{identity.title}</span>
                  </div>
                  {a?.active && running && (
                    <span className="pulse" title={a.waitingOn ? `waiting on ${a.waitingOn}` : "working"} />
                  )}
                </header>

                {!called && <p className="not-called">Not called on this ticket.</p>}

                {a && (
                  <>
                    {a.finding?.summary ? (
                      <blockquote className="says">{a.finding.summary}</blockquote>
                    ) : a.waitingOn ? (
                      // Handed the question over and blocked on the answer.
                      <blockquote className="says thinking">
                        <span className="dots"><i /><i /><i /></span>
                        waiting on {identityFor(a.waitingOn).name}
                      </blockquote>
                    ) : a.saidLast ? (
                      <blockquote className="says thinking">{a.saidLast}</blockquote>
                    ) : a.active ? (
                      // Called, and not back yet.
                      <blockquote className="says thinking">
                        <span className="dots"><i /><i /><i /></span> working
                      </blockquote>
                    ) : (
                      // The run is over. Saying "working" here would be a lie.
                      <blockquote className="says thinking">
                        Took part, but finished without a written answer.
                      </blockquote>
                    )}

                    {a.finding?.recommendation && (
                      <p className="rec">
                        <span className="rec-k">Recommends</span>
                        {a.finding.recommendation}
                      </p>
                    )}

                    {!!a.finding?.blockers?.length && (
                      <ul className="blockers">
                        {a.finding.blockers.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    )}

                    {!!a.finding?.facts_from_mcp?.length && (
                      <details className="facts">
                        <summary>{a.finding.facts_from_mcp.length} facts checked</summary>
                        <ul>
                          {a.finding.facts_from_mcp.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </details>
                    )}

                    <footer>
                      {a.toolsUsed.map((t) => (
                        <span key={t} className="tool"><ToolIcon size={11} />{t}</span>
                      ))}
                      {a.delegatedTo.map((d) => (
                        <span key={d} className="handoff">
                          → {identityFor(d).name}
                        </span>
                      ))}
                      {a.finding?.needs_human_approval && (
                        <span className="needs-you">needs your signature</span>
                      )}
                    </footer>
                  </>
                )}
              </article>
            );
          })}
        </div>
      )}

      {view === "tape" && !idle && (
        <div className="tape">
          {steps.map((step) => {
            const identity = identityFor(step.agent);
            const { label, body } = describeStep(step);
            return (
              <div
                key={`${step.run_id}-${step.seq}`}
                className={`tape-line k-${step.step_type}`}
                style={{ "--ink": identity.ink } as React.CSSProperties}
              >
                <span className="seq">{String(step.seq).padStart(3, "0")}</span>
                <span
                  className="who-mini"
                  style={{ "--ink": identity.ink } as React.CSSProperties}
                  title={identity.name}
                >
                  <AgentIcon role={identity.role} size={12} />
                </span>
                <span className="lbl">{label}</span>
                <span className="body">{body}</span>
                {step.depth > 0 && <span className="depth">d{step.depth}</span>}
              </div>
            );
          })}
          <div className="tape-end" aria-hidden><ReceiptEnd width={160} /></div>
          <div ref={tapeEnd} />
        </div>
      )}
    </div>
  );
}
