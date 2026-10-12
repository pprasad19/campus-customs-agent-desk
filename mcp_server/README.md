# Campus Customs MCP Server

## What it is for

This MCP server is the **only** way the Homework 5 agent team touches shop data.
There is deliberately no second tools layer in `backend/` that reaches around it
into SQLite — if an agent knows a fact about the shop, it came from a tool here.

Every field returned is read straight from the database. If a row does not
exist, the tool reports `found: false` and explains the miss; it never invents a
value, substitutes a default, or estimates.

Several shop rules are enforced **in code here**, not left to the model's
judgement:

- "today" is `desk.date_today`, never the real system clock
- no payment runs without a human approval recorded outside the agent loop
- a payment that would overdraw an account is refused
- a vendor holding an unpaid invoice cannot ship
- stock cannot go negative
- drafts stay on the board; nothing is emailed or sent

Built with **FastMCP** (`from fastmcp import FastMCP`, the standalone `fastmcp`
package). The official `mcp` SDK moved this API — it was `mcp.server.fastmcp` in
1.x and became `MCPServer` in 2.x — and `pydantic-ai` 2.x requires `mcp` 2.x, so
the maintained standalone package is the one that keeps the FastMCP name
available. See the note in `requirements.txt`.

## Which database it uses

| | |
|---|---|
| **Reads and writes** | `data/campus_customs_new.db` — the working copy |
| **Never touches** | `data/campus_customs.db` — the pristine original |

Paths resolve relative to the `Homework 5/` folder, so the server behaves the
same wherever it is launched from. Two environment overrides exist:

- `CAMPUS_CUSTOMS_DB` — point at a different database file. A relative value
  resolves against the project root. **The pristine original is refused as a
  write target**, so a misconfigured run cannot damage the clean copy.
- `CAMPUS_CUSTOMS_OUTPUT_DIR` — point the approval and draft boards somewhere
  disposable, so tests do not write over a real run.

Read-only tools open a read-only connection (`mode=ro`), so a bad query cannot
mutate shop state. Only the write tools open a read-write connection.

To reset the working copy to original values:

```bash
cp -f data/campus_customs.db data/campus_customs_new.db
```

## The tools

21 tools. The tables in brackets are what each one touches.

### Reading shop state

| Tool | Table(s) | What it answers |
|---|---|---|
| `get_shop_date()` | `desk` | What is today, for the shop. Every due-date and overdue judgement uses this. |
| `list_open_tickets()` | `tickets` | What work is outstanding — the team's inbox. |
| `get_ticket(ticket_id)` | `tickets` | One ticket, with its `sku`/`size`/`qty` and its linked `lease_id`/`invoice_id`. |
| `check_inventory_stock(sku, size)` | `inventory` | Units on hand for one SKU **and** size, plus the aisle. |
| `get_sku_pricing(sku)` | `pricing` | `unit_cost`, `list_price`, and the margin between them. |
| `get_lease_rent_due(lease_id)` | `leases`, `desk` | Rent owed, the due date, and days remaining on the shop's calendar. |
| `get_cash_balance(account)` | `cash_accounts` | Cash available — the ceiling on everything the shop can spend. |
| `get_invoice(invoice_id)` | `invoices`, `vendors` | One invoice, the vendor behind it, and whether it is overdue today. |
| `get_vendor_status(vendor_id)` | `vendors`, `invoices` | Lead time **and** `can_ship`, which is false while the vendor holds an unpaid invoice. |
| `list_vendors()` | `vendors` | Who supplies what, with lead times. |
| `list_payments()` | `payments` | Everything already paid, for reconciliation. |

### Approvals — the human gate

| Tool | Writes to | What it does |
|---|---|---|
| `request_payment_approval(kind, ref_id, amount, reason, requested_by, account)` | approval board | Asks a person to approve one payment. **Pays nothing.** Returns an `approval_id` that stays `pending` until a human decides. Flags at request time whether the amount is even affordable. |
| `get_approval_status(approval_id)` | — | Whether a human has decided yet. |
| `request_price_override_approval(ticket_id, sku, size, qty, proposed_unit_price, reason, requested_by)` | approval board | Asks a person to approve selling below list price. **Moves no cash and changes no price.** Reads `pricing` and `inventory` to work out margin, order totals and any stock shortfall itself, so the agent cannot supply flattering figures. |
| `list_approvals()` | — | The whole approval board, payments and decisions alike. |

**There is no approve tool.** Approval happens in `backend/approve.py`, which a
person runs. That is the point: if approving were an MCP tool, an agent could
approve its own payment request.

### Paying and acting

| Tool | Table(s) | What it does |
|---|---|---|
| `pay_invoice(invoice_id, approval_id, account)` | `payments`, `invoices`, `cash_accounts` | Pays a vendor invoice in full. Refuses without a human-approved `approval_id`; refuses if it would overdraw. Writes a `payments` row, lowers the balance, marks the invoice `paid`. |
| `pay_rent(lease_id, approval_id, account)` | `payments`, `cash_accounts` | Pays one month's rent, with the amount taken from the lease so it cannot drift. Same two refusals. Leaves `leases` alone — it has no status or paid-through column. |
| `reduce_inventory_for_sale(sku, size, qty, ticket_id)` | `inventory` | Takes units off the shelf to fulfil an order. Refuses to move more than are on hand. No cash is recorded, because revenue is not modelled. |
| `update_ticket_status(ticket_id, status, note, updated_by)` | `tickets` | Moves a ticket to `open`, `waiting_on_approval`, `waiting_on_vendor`, `resolved` or `refused`, appending a dated note rather than overwriting history. `resolved` and `refused` are final: the tool refuses to move a ticket out of either, so a second agent run cannot reopen a closed ticket or overturn a refusal. Only the desk, which stamps its updates `via the desk`, can. |
| `save_draft_message(ticket_id, audience, subject, body, author)` | drafts board | Saves customer or vendor wording for a human to send. Marked `not_sent_draft_only`. Nothing leaves the building. |

### Approval and draft boards

Both live beside the run output, not in the database:

- `output/approvals.json`
- `output/drafts.json`

They hold process state rather than shop facts, and the given schema has no
table for either. Putting them in the database would mean inventing shop
structure that was not provided.

**Both approval tools refuse a second ask.** If a request for the same obligation is already pending, the existing `approval_id` is handed back rather than a duplicate slip being put in front of the owner. If one was already **declined**, the tool refuses outright: a refusal is an answer, and re-raising it would put a bill the owner turned down back one signature away from being paid.

## Running it

The agents start this server themselves — `.mcp.json` at the project root is the
connection config, and `backend/team.py` loads it with
`pydantic_ai.mcp.load_mcp_toolsets`, so all five agents share one server process.

To start it by hand:

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe mcp_server/server.py
```
