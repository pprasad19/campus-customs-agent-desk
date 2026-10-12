import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { AGENTS, identityFor, summariseByAgent } from "./agents";
import { Crest } from "./components/Icons";
import { TicketRail } from "./components/TicketRail";
import { AgentFloor } from "./components/AgentFloor";
import { CashDrawer } from "./components/CashDrawer";
import { ShiftReportCard } from "./components/ShiftReportCard";
import type {
  AuditStep,
  CashResponse,
  ShiftReport,
  Ticket,
  TicketsResponse,
} from "./types";
import "./styles.css";

/** How often the floor refreshes while a run is in flight. */
const POLL_MS = 1200;

export default function App() {
  const [board, setBoard] = useState<TicketsResponse | null>(null);
  const [cash, setCash] = useState<CashResponse | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [steps, setSteps] = useState<AuditStep[]>([]);
  const [report, setReport] = useState<ShiftReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [justResolved, setJustResolved] = useState<number | null>(null);
  const [showingPastRun, setShowingPastRun] = useState(false);

  const pollRef = useRef<number | null>(null);

  // -- loading ------------------------------------------------------------

  const refreshBoard = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([api.tickets(), api.cash()]);
      setBoard(t);
      setCash(c);
      setOffline(false);
      if (selected === null && t.tickets.length) setSelected(t.tickets[0].id);
    } catch (e) {
      setOffline(true);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [selected]);

  useEffect(() => {
    void refreshBoard();
    // The per-ticket history loads from the selection effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // While nothing is running, keep the drawer in sync so a payment approved in
  // another tab shows up here. This also reconnects on its own: the backend
  // takes a few seconds to attach its MCP server at startup, so a desk opened
  // too early must recover without the person having to reload the page.
  useEffect(() => {
    if (running) return;
    const id = window.setInterval(async () => {
      try {
        if (offline) {
          // Lost the shop. Retry the whole board, and clear the warning on
          // the first call that comes back.
          const [t, c] = await Promise.all([api.tickets(), api.cash()]);
          setBoard(t);
          setCash(c);
          setOffline(false);
          setError(null);
          if (selected === null && t.tickets.length) setSelected(t.tickets[0].id);
        } else {
          setCash(await api.cash());
        }
      } catch {
        setOffline(true);
      }
    }, 3000);
    return () => window.clearInterval(id);
  }, [running, offline, selected]);

  // Show the last run worked on whichever ticket is selected, rather than
  // whatever ran most recently. Selecting #101 and reading a transcript about
  // #103 is worse than showing nothing at all.
  const loadHistoryFor = useCallback(async (ticketId: number) => {
    try {
      const all = await api.events(1000);

      // Ignore everything before the most recent reset. Those runs describe a
      // database state that no longer exists, and showing them on a freshly
      // reset board makes it look as though the work has already been done.
      const lastReset = all.events.map((e) => e.step_type).lastIndexOf("database_reset");
      const since = lastReset >= 0 ? all.events.slice(lastReset + 1) : all.events;

      const matching = since
        .filter(
          (e) =>
            e.step_type === "run_started" &&
            String((e.detail as Record<string, unknown>).scope ?? "") === `ticket ${ticketId}`,
        )
        .map((e) => e.run_id);
      const last = matching[matching.length - 1];
      if (last) {
        const runSteps = since.filter((e) => e.run_id === last);
        setSteps(runSteps);
        setRunId(last);
        setShowingPastRun(true);

        // The closing note belongs to the run being shown, not to whichever run
        // happened to finish most recently. Rebuild it from this run's own
        // report so switching tickets never leaves another ticket's note on
        // screen.
        const finished = [...runSteps]
          .reverse()
          .find((e) => e.step_type === "agent_finished" && e.agent === "boss");
        const past = (finished?.detail as Record<string, unknown> | undefined)?.shift_report;
        setReport((past as ShiftReport | undefined) ?? null);
      } else {
        setSteps([]);
        setRunId(null);
        setShowingPastRun(false);
        setReport(null);
      }
    } catch {
      /* no history yet, or the backend is still waking up */
    }
  }, []);

  useEffect(() => {
    if (selected === null || running) return;
    setReport(null);
    void loadHistoryFor(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, running]);

  // -- the run ------------------------------------------------------------

  const startRun = useCallback(async () => {
    if (selected === null || running) return;
    setRunning(true);
    setError(null);
    setReport(null);
    setSteps([]);
    setJustResolved(null);
    setShowingPastRun(false);

    // Note where the trail already ends, so the floor shows only this run.
    let since = 0;
    try {
      const before = await api.events(1);
      since = before.total_steps;
    } catch {
      /* first run, nothing recorded yet */
    }

    // Poll the audit trail while the team works. The run route only answers
    // once everything is finished, so this is what makes the floor live.
    pollRef.current = window.setInterval(async () => {
      try {
        const e = await api.events(400);
        const fresh = e.events.filter((s) => s.run_id === e.latest_run);
        if (e.total_steps > since && fresh.length) {
          setSteps(fresh);
          setRunId(e.latest_run);
        }
        api.cash().then(setCash).catch(() => undefined);
      } catch {
        /* a dropped poll is not worth surfacing; the next one will catch up */
      }
    }, POLL_MS);

    try {
      const result = await api.runTicket(selected);
      setRunId(result.run_id);
      setReport(result.report);
      const final = await api.events(400, result.run_id);
      setSteps(final.events);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
      setRunning(false);
      const previous = board?.tickets.find((t) => t.id === selected)?.status;
      await refreshBoard();
      const after = await api.tickets().catch(() => null);
      const now = after?.tickets.find((t) => t.id === selected);
      if (now && now.status !== previous) setJustResolved(selected);
    }
  }, [selected, running, board, refreshBoard]);

  useEffect(() => () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
  }, []);

  // -- approvals ----------------------------------------------------------

  const onApprove = useCallback(
    async (approvalId: string, who: string) => {
      const result = await api.approve(approvalId, who);
      await refreshBoard();
      return result;
    },
    [refreshBoard],
  );

  const onReject = useCallback(
    async (approvalId: string, who: string) => {
      await api.reject(approvalId, who);
      await refreshBoard();
    },
    [refreshBoard],
  );

  // -- derived ------------------------------------------------------------

  const activity = useMemo(() => summariseByAgent(steps), [steps]);
  const tickets: Ticket[] = board?.tickets ?? [];
  const current = tickets.find((t) => t.id === selected) ?? null;

  const onDeck = useMemo(() => {
    const live = activity.find((a) => a.active);
    return live ? identityFor(live.role) : null;
  }, [activity]);

  return (
    <div className="desk">
      <div className="desk-grain" aria-hidden />

      <header className="masthead">
        <div className="masthead-left">
          <div className="crest" aria-hidden><Crest size={46} /></div>
          <div>
            <h1>Campus Customs</h1>
            <p className="tagline">
              The back desk · Chapel Street
              {board ? <> · shop date <b>{board.shop_date}</b></> : null}
            </p>
          </div>
        </div>

        <div className="masthead-right">
          {offline ? (
            <div className="lamp off">
              <span className="bulb" />
              Backend asleep
            </div>
          ) : running ? (
            <div className="lamp busy">
              <span className="bulb" />
              {onDeck ? `${onDeck.name} at the counter` : "Team working"}
            </div>
          ) : (
            <div className="lamp on">
              <span className="bulb" />
              Desk open
            </div>
          )}
        </div>
      </header>

      {offline && (
        <div className="alert">
          <b>The desk cannot reach the shop.</b> Start the backend — from the{" "}
          <code>backend/</code> folder run <code>uvicorn main:app --reload --port 8000</code>.
          If it is already starting, give it a few seconds to attach its MCP
          server; this desk retries every three seconds and will clear this
          notice on its own.
          {error ? <div className="alert-detail">{error}</div> : null}
        </div>
      )}

      {error && !offline && (
        <div className="alert soft">
          <b>Something went wrong.</b>
          <div className="alert-detail">{error}</div>
          <button className="ghost" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      <main className="floorplan">
        <TicketRail
          tickets={tickets}
          selected={selected}
          onSelect={setSelected}
          onRun={startRun}
          running={running}
          justResolved={justResolved}
        />

        <section className="stage">
          <AgentFloor
            activity={activity}
            steps={steps}
            running={running}
            runId={runId}
            ticket={current}
            pastRun={showingPastRun}
          />
          {report && <ShiftReportCard report={report} />}
        </section>

        <CashDrawer
          cash={cash}
          ticketId={selected}
          onApprove={onApprove}
          onReject={onReject}
          running={running}
        />
      </main>

      <footer className="colophon">
        <span>Five agents · one MCP server · gpt-6-luna through Portkey</span>
        <span className="dot">•</span>
        <span>{AGENTS.length} desks staffed</span>
        <span className="dot">•</span>
        <span>No payment moves without a signature</span>
      </footer>
    </div>
  );
}
