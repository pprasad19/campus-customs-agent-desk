# Campus Customs — Agent Harness

Working notes for the Homework 5 shop agents. This file grows as the assignment progresses.

- **Original database (never written):** `data/campus_customs.db`
- **Working copy (all writes):** `data/campus_customs_new.db`
- Reset before a full run: `cp -f data/campus_customs.db data/campus_customs_new.db`

Both files currently hash to `23686a90d698f7fa6f901a3f0a9774db` — the working copy starts clean.

---

## Problem 2 — Database survey

### Shop state at a glance

| Fact | Value | Source |
|---|---|---|
| "Today" for the shop | **2026-08-31** | `desk.date_today` |
| Cash on hand | **$3,400.00** (checking) | `cash_accounts` |
| Open tickets | **3** (#101, #102, #103) | `tickets` |
| Payments recorded | **0** | `payments` |

---

### Tables

#### `desk` — 1 row
**Fields:** `date_today` (TEXT, NOT NULL), `notes` (TEXT)

Defines what "today" is for every agent — all overdue and due-date math must read from here, never the system clock.

#### `tickets` — 3 rows
**Fields:** `id` (PK), `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` → `leases.id`, `invoice_id` → `invoices.id`, `status`, `notes`, `created_at`

The agents' inbox and the entry point for every run; its nullable `sku`/`lease_id`/`invoice_id` columns are what connect a request to the rest of the database.

#### `inventory` — 10 rows
**Fields:** `sku` (PK part 1), `name`, `size` (PK part 2), `qty`, `location`

Tells an agent whether a customer order can be filled from stock or has to be sourced from a vendor; keyed by **sku + size**, so stock must always be checked per size.

#### `pricing` — 4 rows
**Fields:** `sku` (PK), `unit_cost`, `list_price`

Supplies the cost and list price behind any quote or discount decision, and is the floor a price override has to be judged against.

#### `vendors` — 3 rows
**Fields:** `id` (PK), `name`, `specialty`, `lead_days`

Determines who can resupply a given product and how long it takes — `lead_days` drives every promised date.

#### `leases` — 1 row
**Fields:** `id` (PK), `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

Holds the shop's recurring rent obligation; `next_due` versus `desk.date_today` decides urgency, and `monthly_rent` is the amount any rent payment must match.

#### `invoices` — 1 row
**Fields:** `id` (PK), `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description`

Tracks what the shop owes vendors; an `open` invoice both creates a payment obligation and blocks that vendor from shipping new product.

#### `cash_accounts` — 1 row
**Fields:** `name` (PK), `balance`, `date`

The single source of truth for affordability — the pay tool must check it before every payment and refuse anything that would drive the balance negative.

#### `payments` — 0 rows
**Fields:** `id` (PK), `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

The audit log of money leaving the shop; starts empty, and its NOT NULL `approved_by` column is where the human-approval requirement is actually enforced and evidenced.

---

### The three open tickets and how they link

#### Ticket #101 — `customer_order` — Tauhid Zaman — "Bulldog tee"
Wants 1 × `CC-TEE-WHITE`, size S.

| Link | Finding |
|---|---|
| → `inventory[CC-TEE-WHITE/S]` | qty **0** — short by 1, cannot fill from stock |
| → `pricing[CC-TEE-WHITE]` | cost $8.00, list $28.00 |
| → `invoices[501]` | $840.00, status **open**, due 2026-08-28 — **overdue by 3 days** |
| → `vendors[1]` | Bulldog Print Co, apparel reprint, **lead 5 days** |

This is the one chained ticket. The tee is out of stock, so it needs a reprint from Bulldog Print Co — but that vendor holds open invoice #501, and the shop rule says a vendor will not ship while an invoice is unpaid. Clearing it is an $840 payment, which requires human approval.

#### Ticket #102 — `rent_notice` — Elm City Properties — "Rent due"
| Link | Finding |
|---|---|
| → `leases[1]` | Chapel Street shop, $2,400.00/mo, next due 2026-09-02 — **in 2 days** |

No product involved. A payment obligation only, and like all payments it needs approval before anything is written to `payments`.

#### Ticket #103 — `price_override` — Yale AI Club — "Bulk hoodie discount"
Wants 20 × `CC-HOOD-NAVY`, size M, at a discount.

| Link | Finding |
|---|---|
| → `inventory[CC-HOOD-NAVY/M]` | qty **8** — short by 12 |
| → `pricing[CC-HOOD-NAVY]` | cost $22.00, list $58.00 → 20 @ list = $1,160.00 |

Two separate problems in one ticket: the discount is a pricing decision against a $22 unit cost, and the quantity cannot be met from stock regardless of price. No invoice or lease link.

### Cash pressure

The two payment obligations total **$3,240.00** against a **$3,400.00** balance:

| Obligation | Amount |
|---|---|
| Invoice #501 (overdue) | $840.00 |
| Rent, due 2026-09-02 | $2,400.00 |
| **Total** | **$3,240.00** |
| Remaining after both | **$160.00** |

Both are payable, but only just. Since cash only flows out in this homework, any further spending — a reprint order for #101, stock for #103 — competes against that $160 remainder, and the pay tool must refuse anything that would overdraw.

### Vendors not referenced by any open ticket

| Vendor | Specialty | Lead days |
|---|---|---|
| Elm City Gifts (#2) | mugs and small goods | 3 |
| QuickShip CT (#3) | local courier | 1 |

Neither is currently blocked by an invoice. Note `inventory[CC-MUG-CREST/OS]` is at qty 0, which is Elm City Gifts' specialty, though no open ticket asks for it.

---

## Problem 3 — MCP server tools

The server lives in `mcp_server/server.py`, is built with FastMCP, and reads the
working copy `data/campus_customs_new.db`. The connection is opened read-only,
so none of these three tools can alter shop state. Every returned field comes
from the database; a missing row returns `found: false` rather than an invented
value.

Each tool takes its arguments directly from the ticket row that needs it, so the
link from ticket to tool is literal rather than thematic:

| Ticket | Ticket fields supplying the arguments | Resulting call |
|---|---|---|
| **101** | `tickets.sku`='CC-TEE-WHITE', `tickets.size`='S' | `check_inventory_stock("CC-TEE-WHITE", "S")` |
| **102** | `tickets.lease_id`=1 | `get_lease_rent_due(1)` |
| **103** | `tickets.sku`='CC-HOOD-NAVY' | `get_sku_pricing("CC-HOOD-NAVY")` |

---

### `check_inventory_stock(sku, size)` → Ticket 101

**Ticket 101** (Tauhid Zaman, `customer_order`) asks for 1 × `CC-TEE-WHITE` in
size S. The agent cannot answer it without knowing whether that exact size is on
the shelf.

- **Reads:** the single `inventory` row matching `sku='CC-TEE-WHITE' AND size='S'`, returning `qty`, `name` and `location`.
- **Returns for this ticket right now:** `qty = 0`, `location = 'Aisle B'`.
- **Decision it unlocks:** 0 on hand against a requested 1 means ticket 101 cannot be filled from stock, which converts it from a pick-and-pack job into a vendor sourcing job and sends the agent to Bulldog Print Co.
- **Why this tool rather than another:** `inventory` is keyed on **sku + size together**, so a SKU-level lookup would report 10 white tees in stock and the agent would wrongly promise the order — only a per-size read exposes that the S row specifically is empty while M, L and XL are not.

### `get_lease_rent_due(lease_id)` → Ticket 102

**Ticket 102** (Elm City Properties, `rent_notice`) says only "shop rent due in
2 days." It names no amount and no date — it carries `lease_id = 1` and nothing
else financial.

- **Reads:** the `leases` row with `id=1`, returning `monthly_rent`, `next_due`, `landlord` and `space_name`; also reads `desk.date_today` to date the comparison.
- **Returns for this ticket right now:** `monthly_rent = $2,400.00`, `next_due = 2026-09-02`, against `today = 2026-08-31` → `days_until_due = 2`, `is_overdue = false`.
- **Decision it unlocks:** it produces the exact figure a rent payment must match ($2,400.00) and confirms the obligation is live but not yet late, which is what lets the agent size the payment against the $3,400.00 balance before requesting approval.
- **Why this tool rather than another:** the ticket's own `notes` field claims "due in 2 days," but that is the landlord's unverified wording — the lease row is the authoritative source, and computing the gap from `desk.date_today` satisfies the shop rule that overdue is measured on the shop's calendar rather than the real clock.

### `get_sku_pricing(sku)` → Ticket 103

**Ticket 103** (Yale AI Club, `price_override`) asks for a bulk discount on 20 ×
`CC-HOOD-NAVY` in size M. A discount cannot be evaluated against a price nobody
has looked up.

- **Reads:** the `pricing` row with `sku='CC-HOOD-NAVY'`, returning `unit_cost` and `list_price`.
- **Returns for this ticket right now:** `unit_cost = $22.00`, `list_price = $58.00`, `margin_per_unit = $36.00` — so 20 units bill at $1,160.00 at list, over $440.00 of cost.
- **Decision it unlocks:** knowing cost is $22.00 fixes the floor beneath which a discount sells at a loss, so the agent can judge any proposed price instead of accepting or refusing the request blind.
- **Why this tool rather than another:** ticket 103 is typed `price_override`, meaning the decision being asked for is a price, and `pricing` is the only table holding what the shop paid — an inventory read would describe availability but says nothing about whether a discount is affordable.

---

### Known gap, deliberately not filled yet

Ticket 101 has a second blocker beyond stock. The reprint would come from
Bulldog Print Co (`vendors.id=1`, `lead_days=5`), which holds open invoice #501
for $840.00, and the shop rules say a vendor will not ship while an invoice is
unpaid. Closing that chain needs a tool over `invoices` and `vendors`, and
settling the invoice needs a pay tool with a human-approval gate. This problem
caps the server at three tools, so both are left for a later problem.

---

## Problem 5 — The agent team

Five Pydantic AI agents, all running **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`
from `.env` in this folder, falling back to one in the folder above). The model
name is a hard-coded constant in
`backend/config.py` with no environment override, so no other model can enter a run.

All five share **one** MCP toolset, loaded from `.mcp.json`. There is no second
shop-tools layer in `backend/` that reaches around the MCP server into SQLite —
every shop fact the agents see arrives through a tool below.

### The five agents

| Agent | Prompt | Owns | Cannot do |
|---|---|---|---|
| **Boss** | `backend/prompts/boss.md` | Runs the shift: reads the ticket list, routes work, weighs tickets against one finite cash balance, writes the final `ShiftReport` | Approve a payment |
| **Inventory** | `backend/prompts/inventory.md` | Per-size stock, vendor choice, lead times, whether a vendor is blocked by an unpaid invoice | Pay or approve anything |
| **Accounting** | `backend/prompts/accounting.md` | Cash, invoices, affordability, raising approval requests, executing *approved* payments | Approve its own request |
| **Facilities** | `backend/prompts/facilities.md` | The lease, rent owed, due dates, the landlord | Pay rent itself |
| **Customer Service** | `backend/prompts/customer_service.md` | Customer-facing wording, discount judgement against unit cost | Change a stored price; send anything |

**Connectivity is complete.** Every agent carries an `ask_<role>` tool for each
of the other four — 20 delegation edges, including a specialist escalating back
to the Boss. Outputs are typed: the Boss returns a `ShiftReport`, specialists
return a `SpecialistFinding` (`backend/models.py`).

### Every MCP tool and the table behind it

| Tool | Table(s) | Reads / Writes | Purpose |
|---|---|---|---|
| `get_shop_date` | `desk` | read | The shop's today. Every date judgement is made against this, never the real clock. |
| `list_open_tickets` | `tickets` | read | The team's inbox for the run. |
| `get_ticket` | `tickets` | read | One ticket with its `sku`/`size`/`qty` and linked `lease_id`/`invoice_id`. |
| `check_inventory_stock` | `inventory` | read | Units on hand for one SKU **and** size. |
| `get_sku_pricing` | `pricing` | read | `unit_cost` and `list_price` — the floor under any discount. |
| `get_lease_rent_due` | `leases` + `desk` | read | Rent owed and days until due on the shop's calendar. |
| `get_cash_balance` | `cash_accounts` | read | The hard ceiling on all spending today. |
| `get_invoice` | `invoices` + `vendors` | read | One invoice, with whether it is overdue today. |
| `get_vendor_status` | `vendors` + `invoices` | read | Lead time **and** `can_ship` — false while the vendor holds an unpaid invoice. |
| `list_vendors` | `vendors` | read | Specialties and lead times, to pick a supplier. |
| `list_payments` | `payments` | read | Everything already paid, for reconciliation. |
| `request_payment_approval` | `cash_accounts` (read), approval board | write (board) | Asks a **human** to approve a payment. Pays nothing. |
| `request_price_override_approval` | `pricing`, `inventory`, `tickets` (read), approval board | write (board) | Asks a **human** to approve selling below list. Moves no cash and changes no price. Margin is computed from the stored cost, not supplied by the agent. |
| `get_approval_status` | approval board | read | Whether a person has decided yet. |
| `list_approvals` | approval board | read | The whole approval board. |
| `pay_invoice` | `payments`, `invoices`, `cash_accounts` | **write** | Pays a vendor invoice. Refuses without human approval; refuses on overdraft. |
| `pay_rent` | `payments`, `cash_accounts` | **write** | Pays one month's rent. Same two refusals. |
| `reduce_inventory_for_sale` | `inventory` | **write** | Takes units off the shelf. Refuses to go negative. |
| `update_ticket_status` | `tickets` | **write** | Records the real outcome and appends a dated note. |
| `save_draft_message` | `desk` (read), drafts board | write (board) | Saves customer or vendor wording for a human. Sends nothing. |

**Two things can wait on a person, and the board holds both.** A `payment`
moves cash and is settled by the pay tools. A `decision` — currently just
`price_override` — moves no cash: approving it writes the agreed terms into the
ticket's history and leaves the `pricing` table alone, because a one-off bulk
deal is not a new list price for every customer. Only payments are counted
against the balance, so a pending discount never misstates what the shop is
about to spend. Ticket 103 is the reason this exists: it is explicitly a
decision ticket, and without it there was nothing on that ticket a human could
actually sign.

The approval board (`output/approvals.json`) and the drafts board
(`output/drafts.json`) sit outside the database on purpose: they are process
state, not shop facts, and the schema has no table for either. Adding tables
would mean inventing shop structure that was not given.

`pay_rent` does not touch `leases` — that table has no status or paid-through
column, so advancing anything there would be inventing a schedule the data does
not record. The payment itself is evidenced in `payments`.

### The audit trail

`output/audit_trail.json` is a JSON array that only ever grows. Each run reads
what is there, appends its own steps, and writes the list back; **no run wipes
it**, so the history survives database resets. If the file is ever unparseable
it is preserved as `audit_trail.corrupt.json` rather than discarded.

One line per agent-loop step, each carrying `run_id`, `seq`, real UTC time, the
shop date, the agent, **who asked it**, and the delegation depth:

| `step_type` | Recorded |
|---|---|
| `run_started` | model, database, shop date, opening cash, every limit in force |
| `agent_started` | the prompt that agent received |
| `model_response` | the text or reasoning it produced |
| `tool_call` | tool name, arguments, call id |
| `tool_result` | the payload the tool returned |
| `delegation` | from, to, the question, and budget consumed so far |
| `refusal` | a refused delegation or a tool retry, with the reason |
| `agent_finished` | the typed output, plus token and request usage |
| `error` / `run_finished` | failure detail, or closing cash and delegations used |

### Safety

**Money.** No payment executes without a human. Agents can only call
`request_payment_approval`, which writes a pending request and pays nothing; the
decision is made by a person through `backend/approve.py`, which is deliberately
*not* an MCP tool so that no agent can approve its own request. An approval is
single-use, non-transferable, and bound to one kind, one reference id and one
exact amount — the pay tools re-check all four and refuse otherwise. Every
payment is reconciled against `cash_accounts` at execution time and refused if
it would overdraw, so the balance cannot go negative even with a valid approval
in hand. Amounts come from the database, never from the model, so a hallucinated
figure cannot be paid. Each payment writes an audit row naming the approver.

**The books.** The pristine `campus_customs.db` is refused as a write target in
code, so a misconfigured run cannot damage the only clean copy. Read-only tools
open a read-only connection, so a bad query cannot mutate state. Ticket notes
are appended, never overwritten, so history is not lost.

**Customers and vendors.** Nothing is sent. Customer and vendor wording is saved
to the drafts board marked `not_sent_draft_only` for a person to review. No
agent can alter a stored price — a price override is a recommendation to the
owner, because discounting is an owner's decision, not an agent's.

**What a real business would also want**, and what this does not yet have: dual
approval above a threshold, a daily spend cap independent of the balance, and a
dry-run mode that reports intended writes without making them.

**Token and loop limits.** Five agents that can all call each other will talk
forever if allowed to. Four caps bound a run, all in `backend/config.py`:

| Limit | Value | Why |
|---|---|---|
| `MAX_DELEGATION_DEPTH` | 3 | Stops long delegation chains; a refused delegation tells the agent to finish with direct tool calls. |
| `MAX_DELEGATIONS_PER_RUN` | 12 | A budget **shared across the whole team**, not per agent, so five agents cannot collectively loop. |
| `TEAM_USAGE_LIMITS` | 100 requests, 160 tool calls, 750k tokens | One hard ceiling for the entire run. Delegated agents run with `usage=ctx.usage`, so a child's tokens count against the same budget as the parent's. A measured single-ticket run used 14 requests and 52k tokens, so this leaves room without leaving the door open. |

There is deliberately **no separate per-specialist limit**. An earlier version had
one, and it was wrong: because every agent shares one usage counter, a
"per specialist" cap of 8 requests was checked against the *team's* accumulated
usage and halted the run as soon as the team as a whole had made 8 calls. Runaway
delegation is held back by depth and the delegation budget instead, which count
the thing that actually loops.

The prompts reinforce the caps: each agent is told that delegation costs a full
model round trip for both parties, not to delegate a lookup it could make in one
tool call, and not to ask two specialists the same question hoping for a better
answer. Delegation returns a compact rendering of the finding rather than raw
JSON, to keep the calling model's context small. Audit fields are trimmed at
4,000 characters so one run cannot produce an unreadable file.

---

## Problem 7 — The FastAPI backend

Started from the `backend/` folder, which serves `http://localhost:8000` for the
dashboard to call:

```
uvicorn main:app --reload --port 8000
```

The API never touches shop data itself. Every shop fact and every payment goes
through the same MCP server the agents use (`backend/mcp_link.py` holds one
client open for the life of the process), so there is still exactly one layer
between the database and everything else.

### Routes

| Route | What it does |
|---|---|
| `GET /tickets` | Returns all three tickets with `status`, plus `is_open` / `is_resolved` flags and the shop date. Reads `tickets` via the MCP tool `list_all_tickets`. |
| `POST /tickets/{ticket_id}/run` | Runs the five-agent team on that one ticket and returns the resulting `ShiftReport`. Makes real `gpt-6-luna` calls; runs are serialised, so a second request gets `409` rather than racing the first. |
| `GET /events` | Returns recent agent-loop steps — what each agent said and every tool it called — newest last, read from `output/audit_trail.json`. Supports `?limit=` and `?run_id=` so the board can refresh cheaply. |
| `POST /approvals/{approval_id}/approve` | **The only thing that moves cash.** Records the human approval with the approver's name, then calls `pay_invoice` or `pay_rent` through MCP. Requires `approved_by`; the pay tool re-checks the approval and the balance and can still refuse. For a `decision` approval it settles the ticket with the agreed terms instead, and no cash moves. |
| `POST /approvals/{approval_id}/reject` | Turns a prepared payment down. No cash moves. |
| `GET /cash` | Returns the current `checking` balance from `cash_accounts`, with payments made so far, the pending approvals queued against that balance, and what would be left if all of them were paid. |
| `POST /reset` | Restores `campus_customs_new.db` from the pristine original for a fresh run, and clears the approval and draft boards. **The audit trail is deliberately kept.** |
| `GET /` | Lists the routes above, the model in use, and which database file is live. |

### Two design decisions worth stating

**Pending approvals are returned by `GET /cash`, not by a separate route.** They
are claims against that exact balance: the dashboard needs their ids to render an
approve button, and the number on its own is misleading without knowing what is
queued to come out of it.

**`POST /reset` clears the boards but keeps the audit trail.** The approval and
draft boards refer to invoices and tickets whose state has just been rolled back,
so a leftover approved request pointing at a now-unpaid invoice would be a live
hazard. The audit trail is the opposite: it is the record of what the agents did
across every run, and wiping it on reset would destroy the evidence that a
repeatable reset exists to produce.

---

# Problem 9 — The finished harness

The sections above record how each piece was built. This one is the reference:
everything that exists, in one place, as it stands after the full run.

---

## 1. The database — 9 tables

Working copy `data/campus_customs_new.db`; pristine original `data/campus_customs.db`,
never written and refused as a write target in code.

| Table | Rows at reset | What it holds | Why the agents need it |
|---|---|---|---|
| `desk` | 1 | `date_today` = **2026-08-31** | The shop's calendar. Every overdue and due-date judgement is made against this, never the system clock. |
| `tickets` | 3 | id, type, requester, sku/size/qty, `lease_id`, `invoice_id`, status, notes | The inbox, and the links from a request to everything else. |
| `inventory` | 10 | sku **+ size** (composite key), qty, location | Whether an order can be filled. Keyed per size, so a SKU-level check is wrong. |
| `pricing` | 4 | unit_cost, list_price | The floor under any discount. |
| `vendors` | 3 | specialty, `lead_days` | Who can resupply, and how long it takes. |
| `leases` | 1 | monthly_rent, next_due | The rent obligation and its real amount. |
| `invoices` | 1 | vendor_id, amount, due_date, status | What is owed, and what blocks a vendor from shipping. |
| `cash_accounts` | 1 | balance = **$3,400.00** | The hard ceiling on all spending. |
| `payments` | 0 | kind, ref_id, amount, paid_at, `approved_by` **NOT NULL** | The audit record of money leaving. The NOT NULL approver is where the approval rule is enforced by the schema itself. |

---

## 2. The five agents

All run **`gpt-6-luna` through Portkey**; the model name is a hard-coded constant
in `backend/config.py` with no environment override. Prompts live one per file in
`backend/prompts/`.

| Agent | Owns | Must not | Output type |
|---|---|---|---|
| **Boss** | Runs the shift, routes work, weighs tickets against one finite balance, writes the report | Approve a payment | `ShiftReport` |
| **Inventory** | Per-size stock, vendor choice, lead times, ship-blocks | Pay or approve | `SpecialistFinding` |
| **Accounting** | Cash, invoices, affordability, raising approvals, executing *approved* payments | Approve its own request | `SpecialistFinding` |
| **Facilities** | Lease, rent owed, due dates, the landlord | Pay rent itself | `SpecialistFinding` |
| **Customer Service** | Customer wording, discount judgement against unit cost | Change a stored price, send anything | `SpecialistFinding` |

**Connectivity is complete** — 20 delegation edges (`ask_<role>` on each of the
five for each of the other four), including specialists escalating back to the
Boss. Delegated runs share the parent's usage counter, so the token ceiling is
team-wide rather than per agent.

---

## 3. MCP tools — 21, one server, one layer

`mcp_server/server.py`, built with FastMCP, launched from `.mcp.json`. Nothing in
`backend/` reaches around it into SQLite.

### Reads (12)

| Tool | Table(s) |
|---|---|
| `get_shop_date` | `desk` |
| `list_open_tickets` | `tickets` |
| `list_all_tickets` | `tickets` |
| `get_ticket` | `tickets` |
| `check_inventory_stock` | `inventory` |
| `get_sku_pricing` | `pricing` |
| `get_lease_rent_due` | `leases` + `desk` |
| `get_cash_balance` | `cash_accounts` |
| `get_invoice` | `invoices` + `vendors` |
| `get_vendor_status` | `vendors` + `invoices` |
| `list_vendors` | `vendors` |
| `list_payments` | `payments` |

### The approval board (4)

| Tool | Touches |
|---|---|
| `request_payment_approval` | reads `cash_accounts`, writes the board. **Pays nothing.** |
| `request_price_override_approval` | reads `pricing`/`inventory`/`tickets`, writes the board. Computes margin itself; idempotent per ticket. **Moves no cash, changes no price.** |
| `get_approval_status` | the board |
| `list_approvals` | the board |

There is deliberately **no approve tool** — approval happens outside the agent
loop, so no agent can approve its own request.

### Writes (5)

| Tool | Tables |
|---|---|
| `pay_invoice` | `payments`, `invoices`, `cash_accounts` |
| `pay_rent` | `payments`, `cash_accounts` |
| `reduce_inventory_for_sale` | `inventory` |
| `update_ticket_status` | `tickets` |
| `save_draft_message` | drafts board (nothing is sent) |

---

## 4. API routes

`backend/main.py`, started from `backend/` with
`uvicorn main:app --reload --port 8000`. Every shop fact and every payment goes
through the MCP server.

| Route | What it does |
|---|---|
| `GET /tickets` | All three tickets with status and open/resolved flags |
| `POST /tickets/{id}/run` | Runs the five-agent team on one ticket; returns the `ShiftReport` |
| `GET /events` | Recent agent-loop steps for the board; `?limit=` and `?run_id=` |
| `POST /approvals/{id}/approve` | **The only thing that moves cash.** Records the approver, then pays through MCP — or, for a decision, settles the ticket with the agreed terms and moves nothing |
| `POST /approvals/{id}/reject` | Turns a request down and records the refusal on the ticket |
| `GET /cash` | Checking balance, payments made, and the approvals queued against it |
| `POST /reset` | Restores the working DB from the original; clears the boards; **keeps the audit trail** |
| `GET /` | Lists the routes, the model and the live database |

---

## 5. Safety rules

**Money.** No payment executes without a human. Agents may only *request*;
`backend/approve.py` and the approve route are outside the agent loop. An
approval is single-use, non-transferable, and bound to one kind, one reference
and one exact amount — all four re-checked at payment time. Every payment is
reconciled against `cash_accounts` and refused if it would overdraw, even with a
valid approval in hand. Amounts come from the database, never from the model.
Each payment writes `approved_by`.

**The books.** The pristine database is refused as a write target in code.
Read-only tools open read-only connections. Ticket notes are appended, never
overwritten.

**Customers and vendors.** Nothing is ever sent; wording is saved to the drafts
board marked `not_sent_draft_only`. No agent can alter a stored price — a
discount is a recommendation to the owner.

**Dates.** "Today" is `desk.date_today`. No system clock anywhere in the tools.

**Token and loop limits** (`backend/config.py`): delegation depth 3, a team-wide
budget of 12 delegations per run, and one shared `TEAM_USAGE_LIMITS` of 100
requests / 160 tool calls / 750k tokens. There is no separate per-specialist
limit, because every agent shares one usage counter and a smaller cap would be
measured against the team's total.

**Still missing, in fairness:** dual approval above a threshold, a daily spend
cap independent of the balance, and a dry-run mode.

---

## 6. The dashboard

React + Vite + TypeScript in `frontend/`, served by `npm run dev` on
`localhost:5173`, talking to `localhost:8000`. Design rationale in
`output/design.md`.

- **The spike** (left) — every ticket as a slip with its product drawn on it,
  status pill, and a rubber stamp on terminal outcomes. The brass bell starts a run.
- **The floor** (centre) — one card per agent, each with a portrait, what it
  concluded, what it recommends, its blockers, and the tools it touched. Agents
  *not* called stay visible but dimmed, so over-delegation is as readable as
  delegation. A **Tape** view shows every audit step in sequence.
- **The drawer** (right) — the balance, a signature line, and anything waiting on
  a person: brass cheques for payments, violet slips for price decisions with
  their own cost/margin arithmetic. Approving is the only action that moves money.

Selecting a ticket loads that ticket's own last run from the audit trail.

---

## 7. What the full run produced

Reset to `$3,400.00`, then the team worked each ticket and three decisions went
to a human, all approved.

| Ticket | Final status | Agents | Cash |
|---|---|---|---|
| **101** tee order | `resolved` | Boss, Inventory, Accounting | **−$840.00** (invoice 501, approved) |
| **102** rent | `resolved` | Boss, Facilities, Accounting | **−$2,400.00** (rent, approved) |
| **103** discount | `resolved` | Boss, Customer Service, Inventory | $0.00 (price approved, not a purchase) |

**$3,400.00 − $3,240.00 = $160.00**, matching `cash_accounts.balance` exactly.
Two rows in `payments`, both naming the owner as approver, both dated on the
shop's own date 2026-08-31.

### What `resolved` means here

**Closed from the shop's side**: everything Campus Customs could do today has
been done and no further move is available to it. It does **not** claim the
customer has their goods, and where something is still outstanding the ticket
note says exactly what:

- **101** — the debt is cleared and Bulldog Print Co is unblocked, but size S is
  still at 0 and no reprint was ordered. The vendor's real reprint price is
  recorded nowhere and only $160.00 of cash remains. Tauhid has no tee.
- **103** — the $46.00 price is agreed, but only 8 of the 20 hoodies exist and
  the missing 12 would cost $264.00 against $160.00 of cash. The Yale AI Club has
  a price, not twenty hoodies.
- **102** — genuinely finished. The landlord has the money.

`output/resolved_tickets.json` records this per ticket under `still_outstanding`,
so a closed ticket can never quietly hide an unmet promise. The alternative —
leaving them open forever — would have been just as untrue, because the shop
really had run out of moves.

**Zero payments were made by an agent.** All three decisions were raised by the
team and taken by a human.

**An approved decision is not a purchase.** Ticket 103's price override was
approved and still moved $0.00. Counting it against the balance would understate
what the shop holds.

### Where the plan was right, and where it was wrong

**Right:** the per-size stock trap on 101, the vendor blocked by an unpaid
invoice, Accounting weighing that invoice against the competing rent, Facilities
reading the lease rather than trusting the landlord's wording, and the unit cost
as the floor under the discount on 103.

**Wrong, or not deterministic:**

1. **The mesh is mostly used as a star.** Nearly every delegation runs
   Boss → specialist. An earlier run of ticket 102 did produce
   Facilities → Accounting, so the capability works and the shape simply varies
   between runs.
2. **The Boss does much of the lookup itself**, delegating mainly what it cannot
   do — the money and the price.
3. **Customer Service was never called on 101**, so the customer waiting on the
   tee has still not been written to.

### Artifacts from this run

| File | What it holds |
|---|---|
| `output/desk_tickets.html` | Expected vs Actual per ticket, the itemised Cash tab, and the reflection |
| `output/resolved_tickets.json` | Final status, outcome, what is still outstanding, per-agent contribution and the human decision per ticket |
| `output/resolved_board.html` | Screenshots of the live dashboard for each ticket |
| `output/audit_trail.json` | Every step of every real run, appended, never wiped |
| `output/approvals.json` · `output/drafts.json` | The signed decisions and the unsent drafts |
