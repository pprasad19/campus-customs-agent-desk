# The Back Desk — design notes

What the Campus Customs dashboard looks like, and why it was built that way.

## The governing idea: a desk, not a console

Campus Customs is a small shop on Chapel Street with one cash account, three
paper tickets and a landlord who emails. The software that runs it should feel
like the back desk of that shop — paper, ink, a brass bell, a till — rather than
a generic analytics console with cards and sparklines.

That decision drove everything else. The question asked of each element was not
"what widget shows this data" but **"what object on a real desk does this job"**:

| The job | The object |
|---|---|
| Work waiting to be done | Paper slips on a spike |
| Starting the team | A brass counter bell |
| Watching people work | Nameplates at five desks |
| Every step, in order | A till roll of receipt tape |
| Money | A weighted cash drawer |
| Authorising a payment | A cheque you sign by hand |
| A finished job | A rubber stamp |

The payoff is that someone who has never seen the app can read the screen in a
few seconds, because they already know what a spike of receipts and a signature
line mean.

## Layout: three zones, left to right, in the order work moves

The screen is a fixed three-column floorplan, which maps onto how a job actually
travels through the shop:

**Left — the spike.** Every ticket, as a cream paper slip with a punched hole at
the top where the spike goes through, ruled lines showing faintly through the
paper, and a slight lift and rotation on hover as though you were thumbing
through them. The selected slip gets a brass ring. Underneath sits the bell.

**Centre — the floor.** Where the five agents work. This is the largest zone
because watching the team is the point of the application.

**Right — the drawer.** The balance, the signature line, and any payment waiting
on a human. Deliberately the narrowest column but the highest contrast one, so
money is always in peripheral vision without dominating.

Both outer columns are sticky; the centre scrolls. You never lose sight of the
balance while reading a long transcript, which matters when the whole point is
noticing that an agent is about to spend money.

Below 1240px the drawer drops to a full-width band underneath; below 880px it
becomes a single column. The reading order survives both.

## How the agents read differently from each other

This was the hardest problem. Five agents producing text could easily collapse
into one undifferentiated wall. Four separate signals keep them apart, so you can
tell who is speaking **before** you read a word:

1. **Ink colour.** Each agent owns a hue, chosen for meaning rather than variety:
   the Boss in **burnt amber** (warm, in charge), Inventory in **green** (stock,
   growth), Accounting in **oxblood red** (money, caution), Facilities in
   **indigo** (property, permanence), Customer Service in **teal** (the outward
   face). The colour appears in the left border of the desk card, the speech
   block, the monogram plate and the tape line, so it is reinforced four times.

2. **A monogram plate.** A single letter on a tinted plate — B, I, A, F, C — in
   the serif face. It reads as an engraved nameplate on a desk, and it is what
   makes the tape scannable at a glance.

3. **Position.** The five desks never move. Learning the layout once means later
   runs are read by muscle memory.

4. **Presence.** Agents not called on a ticket stay on screen but drop to 50%
   opacity with a greyed border and the line *"Not called on this ticket."* This
   is a deliberate design choice rather than hiding them: **who the Boss did not
   call is as informative as who it did.** A run where all five light up on a
   rent notice is a run that over-delegated, and the interface should make that
   obvious rather than conceal it.

The agent currently working gets a pulsing dot, a lift, and a coloured halo —
the "at the counter" state — and the lamp in the masthead names them.

### Two ways to watch

A toggle offers **Desks** or **Tape**.

- **Desks** is the human view: one card per agent with what they concluded, what
  they recommend, their blockers, the tools they touched as small monospace
  chips, and arrows showing who they handed off to. Facts checked are collapsed
  behind a disclosure so the card stays calm but the evidence is one click away.
- **Tape** is the forensic view: every audit step in sequence on a receipt roll,
  with alternating paper bands, sequence numbers, delegation lines tinted brass,
  refusals and errors in red, and a depth marker on anything nested. It
  autoscrolls while the team works.

The same run, two reading speeds. You skim the desks; you audit the tape.

## How resolved tickets show up

A finished ticket gets a **rubber stamp** — rotated eight degrees, double-ruled
border, ink-faded, sitting at an angle no digital element would naturally take.
Green for `RESOLVED`, rose for `REFUSED`.

The stamp is reserved for those two terminal outcomes. An earlier version stamped
every non-open ticket, including the waiting ones, and the rotated text lay
straight across the slip's own content — unreadable. A ticket that is merely
waiting already says so in its status pill, which is quieter and clearer.

When a run finishes and the status actually changes, the stamp **lands**: it
drops in at 2.6× scale, overshoots slightly past its resting size, and settles,
on a spring curve over about half a second. It is the one piece of motion in the
app allowed to be theatrical, because finishing a ticket is the moment worth
celebrating, and a stamp thumping down is the physical gesture everyone already
associates with "done."

The slip also fades to a slightly warmer, flatter paper and its status pill
switches colour, so the state is legible even with motion disabled.

## How cash shows up

The till is the only dark object on the desk — deep Yale navy with a brass top
edge — so the eye goes to it immediately. The balance is set large in the serif
face with tabular figures, so digits do not jitter as they change.

**It never snaps.** When money leaves, the number *counts down* over 850ms on an
eased curve while the whole drawer does a short vertical bounce and takes a brass
glow. You feel the money go. A balance that silently changes from 3,400 to 2,560
between renders is exactly the kind of thing a person should never miss, and
animation is the cheapest way to guarantee they do not.

Underneath, the drawer shows what is *claimed* against the balance — the pending
total and what would be left if every waiting payment were approved. The number
that matters is rarely today's balance; it is the balance after everything queued
up has gone out.

## The signature, and the moment of consent

This is the part the whole design is built around.

The agents can prepare a payment. **Only a human signature moves money**, and the
interface makes that asymmetry physical rather than stating it in a tooltip:

- There is a **signature field** styled as a ruled line, in the large serif face,
  with an italic *"your name"* placeholder — it looks like somewhere you sign,
  not a form input.
- Approving with the field empty is refused in the browser with *"Sign your name
  first — an approval has to name a person."* The backend requires it too; the
  front end simply refuses to let you get there carelessly.
- Each waiting payment is a **cheque**: brass top edge, the amount in large
  serif, the agent's stated reason in prose, who asked and when, and the approval
  id ghosted in the bottom corner like a serial number.
- Every cheque states its consequence before you act: *"Leaves $2,560.00 in
  checking."* If the payment would overdraw, the cheque turns red-edged and the
  line becomes *"Would overdraw by $X — the shop will refuse this,"* so you learn
  the outcome before clicking rather than after.

Adding friction to a button is usually bad design. Here it is the entire point:
this is the one irreversible action in the application.

## The other thing a human signs: a price

Not everything waiting on a person is a payment. Ticket 103 asks for a discount —
an owner's decision that moves no cash at all — and for a while the desk had
nothing to offer it, because the approval board only accepted payments. A ticket
explicitly about a decision had no decision to make.

Both now share one queue, because "what is waiting on me?" should have a single
answer, but they are drawn so you cannot confuse them:

| | Payment cheque | Price call |
|---|---|---|
| Top edge | brass | **violet** |
| Headline figure | the amount leaving the account | the **per-unit price** being proposed |
| Consequence line | "Leaves $2,560.00 in checking" | "No cash moves. Stock covers all 20 units." |
| Button | **Approve & pay** | **Approve price** |

A price call also carries something a cheque never needs: **the arithmetic**. A
four-cell grid shows cost each, margin each, order total and total margin, so the
question "is $46 a good price?" is answerable on the slip itself rather than in
your head. Margins at or below zero turn rose.

Two warnings are specific to this slip. If the proposed price is below unit cost,
the slip turns red-edged and says every unit sells at a loss. If stock cannot
cover the order, an amber line says so and makes clear that approving agrees the
*price* but not the supply — because agreeing a price for twenty hoodies when
eight exist is exactly the kind of quiet over-promise this interface is meant to
prevent.

Crucially, the pending total in the till **excludes** price calls. They are
waiting on you, but approving one takes nothing out of the account, and letting a
discount inflate "awaiting your signature" would misstate what the shop is about
to spend.

## Showing state honestly

A dashboard that quietly misreports itself is worse than no dashboard, and three
of the sharper corrections during this build were all versions of the same
mistake: the screen saying something that was not true.

**An agent that has finished does not say it is working.** The Boss's card used
to show a thinking animation forever, because specialists report a
`SpecialistFinding` and the Boss reports a `ShiftReport` — a different shape
entirely — and the card only knew how to read the first. The Boss's report is now
translated into the same form, so its card shows what it concluded per ticket,
the reasoning behind it, and what it left for you. If an agent genuinely produced
nothing, the card says *"Took part, but finished without a written answer"*, which
is true, instead of claiming it is still busy. The pulsing dot and glow only
appear while a run is actually in flight.

**Internal machinery is not displayed as shop work.** `final_result` — the
mechanism the agent framework uses to collect a structured answer — was appearing
in the tool list beside real tools like `get_cash_balance`, implying the shop had
done something it had not. It and the `ask_*` handoffs are filtered out; handoffs
get their own chips.

**History survives a refresh.** The floor used to start empty, so reloading after
a run made it look as though nothing had ever happened. It now loads the most
recent run from the audit trail and labels it **LAST RUN**, so you can read what
the team did without having to run them again.

**The desk reconnects on its own.** The backend takes a few seconds to attach its
MCP server at start-up, and a page opened in that window used to stay stuck on
"Backend asleep" until manually reloaded. It now retries every three seconds and
clears the warning itself, and the message says so, so a momentary gap looks like
a momentary gap rather than a dead application.

## Typography and palette

**Fraunces** — a warm, slightly old-style serif — carries headings, the balance,
the amounts and the signature. **Inter** carries interface text, where clarity
beats character. **JetBrains Mono** carries tool names, ids and raw tool
results, which should look like machine output because that is what they are.

The palette is a **night shop**: a deep indigo canvas (`#0e1222`) lit by three
soft coloured glows — azure at the top left, violet at the top right, brass at
the bottom — so the background has depth instead of being a flat dark
rectangle. Over it sits a faint starfield of single pixels at three different
scales, which keeps large empty areas from looking like dead space.

Dark was chosen over the earlier cream paper for a specific reason: this screen
is mostly *status*, and status reads better as light on dark. A glowing green
lamp, an amber cheque waiting to be signed and a red overdraft warning all pop
off an indigo field in a way they never did off beige.

Five accent hues carry meaning, never decoration:

| Colour | Means | Where it appears |
|---|---|---|
| **Brass** `#f0a93b` | money, and anything awaiting a human | the till, the bell, payment cheques, the Boss |
| **Azure** `#4f9dff` | the shop itself | masthead, customer tickets, the shift report |
| **Mint** `#3ddc9a` | good, done, approved | the open lamp, resolved stamps, Approve buttons, Inventory |
| **Rose** `#ff6b81` | refused, overdrawn, below cost | overdraft warnings, blockers, Accounting |
| **Violet** `#a98bff` | a decision rather than a payment | price-call slips, the lease, Facilities |

The masthead wordmark is a gradient from brass through white to azure, and a
hairline of all four accents runs along its bottom edge — a small signature that
ties the whole palette together in one strip.

## The artwork

Every illustration is **inline SVG drawn for this project**. Nothing is loaded
from a CDN or an image file, so the desk stays self-contained, stays crisp at
any zoom, and inherits colour from whatever state it is in.

**Product art on every slip.** Each ticket carries a small drawing of the thing
being asked about — a tee, a hoodie, a cap, a mug — picked from the SKU. Ticket
101 shows a t-shirt, 103 shows a hoodie, and a ticket with no product (the rent
notice) shows a key instead. It means you recognise a ticket by its shape before
you read a word of it, and it makes the board feel like a shop rather than a
queue.

**The storefront.** The idle floor shows Campus Customs itself: a striped awning
with scalloped edge, two lit windows with a tee and a mug hanging inside, a
door, and the shop name on the sign. It is the single piece of real warmth in
the interface, and it turns the "nothing is happening yet" state from an absence
into a place.

**Agent badges instead of initials.** Each agent now has a drawn glyph rather
than a letter: a crown for the Boss, a crate for Inventory, stacked coins for
Accounting, a building for Facilities, a speech bubble for Customer Service.
Tinted with that agent's hue, they identify a speaker instantly — in the desk
cards, in the idle line-up, and as 20px chips down the left of the tape.

**Character portraits at the desks.** Each agent is drawn as a person rather
than a symbol: a shared silhouette of head and shoulders, differentiated by
hairstyle and by the prop of their trade — a clipboard for the Boss, a crate for
Inventory, a coin for Accounting, a key for Facilities, a headset for Customer
Service. Tinted in that agent's hue inside a circular frame, they make the floor
read as five colleagues at work instead of five status cards. The portrait
brightens and gains a ring when its agent is the one speaking, and desaturates
for anyone not called on the ticket.

**A merch pattern behind the masthead.** Tees, hoodies, caps and mugs tile
faintly across the header at 14% opacity in brass line-work — enough to read as
a shop's own stationery, far too faint to compete with the wordmark.

**A hero for the selected ticket.** Between runs, a strip above the floor shows
the chosen ticket's product drawn large on a soft radial glow, gently floating,
beside its number, subject, requester and status. It keeps what you are about to
work in front of you while you read what happened last time, and it gives the
largest panel on the page something to look at when no agent is talking.

**An all-clear illustration** replaces the bare "nothing waiting on you" line in
the drawer: a clipboard with a green tick. An empty queue is good news, and it
should look like good news rather than like missing content.

**Functional icons** mark the bell, the till, the signature line, tool chips,
and every warning. The rule applied throughout: an icon only exists where it
replaces a word or speeds up a scan, never as ornament beside a label that
already says the same thing.

## More artwork

**A watermark behind every desk.** Each agent's card carries a large line
drawing of their trade at 7% opacity, bleeding off the bottom-right corner: the
Boss's counter bell, Inventory's stocked shelving, Accounting's stacked coins,
the Facilities shopfront, Customer Service's letters. It gives five otherwise
identical cards their own texture. The watermark brightens to 16% and tilts
slightly when that agent is the one speaking, which is a second, peripheral way
of noticing who is active — and fades to 4% for anyone not called.

**A delivery van** parks in the corner of any ticket waiting on a vendor,
rocking very slightly as though idling. "Waiting on a vendor" is the least
self-explanatory status in the system, and a van says it faster than the words
do.

**A ledger** sits beside the closing note, and **a torn receipt edge** caps the
bottom of the tape view, so the till roll ends the way a real one does rather
than just stopping.

## Effects

Motion is used to show state — something arriving, something working, something
leaving. Nothing moves purely as decoration.

**An aurora behind everything.** Two blurred colour fields drift across the
background on 34-second and 46-second cycles, in opposite directions. Far too
slow to watch, but it stops a mostly-dark page from looking like a flat
rectangle, and it means the desk never appears frozen even when nothing is
happening.

**Staggered entrances.** Ticket slips and desk cards rise and fade in on a
spring curve, each a few hundredths of a second after the last. The effect is
that a run *populates* the floor rather than flashing it into place, which makes
the five agents feel like they are arriving at their desks.

**A sweep across the bell.** A soft diagonal highlight travels over the brass
every six seconds. It marks the bell as the one thing on the page you are meant
to press. An early version used a brighter sweep and briefly washed out the
label underneath; it is now dimmed and set to `soft-light` so it reads as polish
on metal rather than a flash.

**A progress shimmer while the team works.** A brass-and-violet band travels
along the bottom edge of the floor header for exactly as long as a run is in
flight. Agent runs take minutes, and a dashboard with no pulse during that time
looks hung rather than busy.

**A breathing glow on the active agent**, cycling every 2.4 seconds, so the
agent currently at the counter is findable from the corner of your eye.

**A glint across the till** when money leaves — a highlight sweeps the brass
once, alongside the counting balance and the drawer's bounce. Three signals for
one event, because that event is cash leaving the business.

**A slow float** on the storefront and on the selected ticket's hero, roughly
one cycle every four to seven seconds, with each element on its own timing so
nothing marches in step.

**A soft pulse** on any `waiting on you` status pill, which is the one state
that needs a human to do something.

Every one of these is disabled under `prefers-reduced-motion`, and none of them
carries information on its own — every animated state also has a static colour,
label or icon saying the same thing.

## The small things that make it feel like somewhere

- **The lamp.** A pill in the masthead with a coloured bulb: green "Desk open",
  pulsing brass "*Accounting* at the counter" with the live agent's actual name,
  red "Backend asleep". One glance tells you the state of the whole system.
- **The bell.** Brass gradient, an inset highlight along the top edge, and it
  depresses on click with the shadow inverting — a real button being pressed. Its
  subtitle reads "start the team on #101", so you always know what you are about
  to set in motion.
- **The empty state.** Five monogram plates breathing gently out of phase above
  *"Five desks, all quiet."* Not a spinner, not an empty box — the staff waiting.
- **The closing note.** The shift report renders as a memo: opening balance, an
  arrow, closing balance, a pill saying how much went out, then one verdict block
  per ticket colour-coded by outcome, with a **"Because"** line carrying the
  reasoning. Anything left for a person appears in an amber "Left for you" panel.
- **Honest failure.** If the backend is down, the desk says so plainly and gives
  the exact command to start it, rather than spinning forever.
- **`prefers-reduced-motion` is respected.** The stamp, the counting balance and
  the pulses all collapse to instant for anyone who asks for that. None of the
  information is carried by motion alone — every animated state also has a static
  colour or label.

## What the polish is actually for

The decorative choices are not decoration. The stamp exists so a finished ticket
is unmissable. The counting balance exists so money leaving is unmissable. The
dimmed desks exist so over-delegation is unmissable. The signature line exists so
nobody approves a payment by reflex.

A desk someone enjoys sitting at is a desk they will actually watch — and the
whole safety argument of this system rests on a human paying attention at exactly
one moment: the signature.
