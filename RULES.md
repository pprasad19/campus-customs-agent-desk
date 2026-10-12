# Rules of this shop

Transcribed from the assignment. These are hard constraints for Homework 5.

## Time and overdue
- The field `desk.date_today` is "today" for the shop. Use this date to determine what is overdue.
  - Do **not** use the real system clock.

## Vendors
- Vendor lead times come from the `vendors` table.
- A vendor will **not** ship new product while they still have an open unpaid invoice.

## Payments and cash
- **Human approval is required for any payments.** Points will be deducted if this is not done.
- If payment is made, make sure to update the relevant table.
- If there is not enough cash, the pay tool **must refuse** — no negative balances.
- Cash only goes **out** in this homework — revenue is not modeled, so no money comes in.

## Runs
- Before a full run to resolve the tickets, reset the database to the original values.

## External contact
- Do **not** email customers or call real vendors. Drafts stay on the board.

## Model
- Use `PORTKEY_API_KEY` for AI calls.
- Use **only** `gpt-6-luna` through Portkey, for every agent.
- Points will be deducted if any other model shows up in the code or in runs.

---

## Local setup notes

- Working database (all writes): `data/campus_customs_new.db`
- Pristine original (never written): `data/campus_customs.db`
- Reset before a full run:

```bash
cp -f "data/campus_customs.db" "data/campus_customs_new.db"
```
