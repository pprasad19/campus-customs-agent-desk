# Campus Customs — a five-agent shop desk

Campus Customs is a small campus merchandise shop in New Haven with three open
tickets, one cash account, and a landlord. This project runs it with a team of
five AI agents — a Boss, Inventory, Accounting, Facilities and Customer Service —
working behind a dashboard that a person actually sits at.

The central rule: **the agents can prepare a payment, but only a human signature
moves money.**

---

## What is in here

| Path | What it is |
|---|---|
| `data/campus_customs.db` | The original shop database. Never written to — it is the reset source. |
| `data/campus_customs_new.db` | The working copy. Everything the agents do happens here. |
| `mcp_server/server.py` | The MCP server: the only way anything reaches the shop database. 21 tools. |
| `backend/` | FastAPI app, the five agent prompts, and the agent team itself. |
| `frontend/` | The React dashboard — the desk. |
| `output/` | Everything produced along the way: the plan, the audit trail, the results, the reflection. |

Open `output/desk_tickets.html` in a browser to see the plan, what the agents
actually did, the cash reconciliation and the written reflection. Open
`output/resolved_board.html` for screenshots of the live dashboard.

---

## Setup, once

You need **Python 3.11+** and **Node 18+**.

### 1. Python environment

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt     # Windows
.venv/bin/python -m pip install -r requirements.txt             # macOS / Linux
```

### 2. The API key

Every agent uses `gpt-6-luna` through Portkey. Copy the example file and add
your key:

```bash
cp .env.example .env
```

Then edit `.env` and set `PORTKEY_API_KEY=...`. **The real `.env` is never
committed** — only `.env.example` is.

### 3. Frontend dependencies

```bash
cd frontend
npm install
```

---

## Copying the original database to the working copy

Do this whenever you want a clean shop. It overwrites the working copy with the
untouched original, so the balance returns to **$3,400.00** and all three tickets
return to `open`:

```bash
cp -f data/campus_customs.db data/campus_customs_new.db
```

On Windows PowerShell:

```powershell
Copy-Item -Force data\campus_customs.db data\campus_customs_new.db
```

The original is never written to by anything in this project — the MCP server
refuses it as a write target in code — so it is always safe to copy from.

---

## Starting the MCP server

**You do not normally need to start this yourself.** The MCP server is launched
automatically, as a child process, by whatever needs it:

- the FastAPI backend starts one when it boots, and
- the agent team starts one when a run begins,

both using the connection settings in `.mcp.json` at the project root.

To run it by hand — useful if you want to check it loads, or connect it to
another MCP client:

```bash
.venv/Scripts/python.exe mcp_server/server.py      # Windows
.venv/bin/python mcp_server/server.py              # macOS / Linux
```

It speaks the MCP protocol over stdin/stdout, so on its own it will print a
banner and then sit waiting. That is correct. Press Ctrl+C to stop it.

It reads `data/campus_customs_new.db`. Point `CAMPUS_CUSTOMS_DB` at a different
file to override that — it must still be a working copy, never the original.

---

## Starting the FastAPI backend

From the `backend/` folder:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

That serves **http://localhost:8000**. Give it a few seconds on startup — it
launches the MCP server as a child process before it begins answering, and until
that finishes the dashboard will say "Backend asleep".

Check it is alive by opening <http://localhost:8000/> which lists every route.

| Route | What it does |
|---|---|
| `GET /tickets` | The three tickets and whether each is open or resolved |
| `POST /tickets/{id}/run` | Runs the five-agent team on one ticket. Refuses a ticket that is already `resolved` or `refused` |
| `GET /events` | Recent agent steps, so the board can show live progress |
| `POST /approvals/{id}/approve` | **The only thing that moves cash** |
| `POST /approvals/{id}/reject` | Turns a prepared payment or price down. Needs a name, same as approving |
| `GET /cash` | The checking balance and anything waiting on a signature |
| `POST /reset` | Restores the database to original values. Refuses while a run is in progress |

---

## Starting the React board

From the `frontend/` folder, with the backend already running:

```bash
cd frontend
npm run dev
```

This opens the desk in your browser automatically, normally at
**http://localhost:5173**. If that port is already in use, Vite will step to
5174 or 5175 — all three are accepted by the backend, so the desk works either
way. Check the browser tab says *Campus Customs — The Back Desk* so you know you
are looking at the right app.

Using the desk:

1. Pick a ticket from the spike on the left.
2. Press **Ring the bell** to start the agent team on it. Watch the floor —
   whichever agent is working lights up, and the Boss shows "waiting on …" while
   a specialist answers.
3. When the run finishes, anything needing a decision appears in the drawer on
   the right. **Type your name in the signature field**, then approve or decline.
4. The balance drops only when you approve a payment.

---

## Resetting before a full three-ticket run

The shop rules ask for a clean database before working all three tickets, so the
run starts from a known position. Either way works:

**From the dashboard or any HTTP client:**

```bash
curl -X POST http://localhost:8000/reset
```

**Or by copying the file directly**, with the backend stopped:

```bash
cp -f data/campus_customs.db data/campus_customs_new.db
```

The reset route is the better option while the app is running, because it also
clears the approvals and drafts boards — stale approvals left pointing at bills
that are unpaid again would be a real hazard.

**The audit trail is never cleared.** `output/audit_trail.json` only ever grows,
so the history of every run survives every reset. A marker line is written into
it each time you reset, and the dashboard uses that marker to avoid showing you
runs from before the rollback.

After a reset you should see:

- checking balance **$3,400.00**
- **0** payments on record
- tickets 101, 102 and 103 all `open`

### A full run, start to finish

```bash
# 1. clean shop
curl -X POST http://localhost:8000/reset

# 2. work each ticket (or press Ring the bell three times in the dashboard)
curl -X POST http://localhost:8000/tickets/101/run
curl -X POST http://localhost:8000/tickets/102/run
curl -X POST http://localhost:8000/tickets/103/run

# 3. sign the decisions in the dashboard drawer, then check the money
curl http://localhost:8000/cash
```

With all three approved, the shop pays $840.00 for the overdue vendor invoice and
$2,400.00 for rent, finishing on **$160.00**.

---

## A note on what "resolved" means here

A ticket is `resolved` when **Campus Customs has done everything it can do today
and no further move is available to it**. It does *not* claim the customer has
their goods.

`resolved` and `refused` are both **final**. Once a ticket reaches either, the
agents cannot move it again — ringing the bell a second time on a closed ticket
leaves it closed, and a refusal you signed is not something an agent can
overturn on a later run. Only you can change a closed ticket, from the desk.

That distinction matters on this board. All three tickets are resolved, but only
the rent was genuinely delivered — the landlord has the money. The other two
closed with work still outstanding, and each says so in its own notes:

- **101** — the overdue invoice was paid and Bulldog Print Co is unblocked, but
  size S is still at zero and no reprint was ordered. The shop has no tool for
  placing a vendor order, and only $160.00 of cash remains. Tauhid has no tee.
- **103** — a $46.00 bulk price was agreed with the owner, but only 8 of the 20
  hoodies exist and the missing 12 would cost $264.00 against $160.00 of cash.

Nothing here invents stock, moves the shop's date, or fakes a payment. Where a
promise is unmet, the ticket note, the `still_outstanding` field in
`output/resolved_tickets.json`, and `output/desk_tickets.html` all say so.
