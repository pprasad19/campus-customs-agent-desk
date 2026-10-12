import type { Ticket } from "../types";
import { BellIcon, ProductArt, TicketTypeIcon, VanArt } from "./Icons";

const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  waiting_on_approval: "Waiting on you",
  waiting_on_vendor: "Waiting on vendor",
  resolved: "Resolved",
  refused: "Refused",
};

interface Props {
  tickets: Ticket[];
  selected: number | null;
  onSelect: (id: number) => void;
  onRun: () => void;
  running: boolean;
  justResolved: number | null;
}

/** The spike of paper slips on the left of the desk. */
export function TicketRail({
  tickets,
  selected,
  onSelect,
  onRun,
  running,
  justResolved,
}: Props) {
  const openCount = tickets.filter((t) => t.is_open).length;

  // A closed ticket is not worked again: `resolved` means the shop ran out of
  // moves, `refused` means the owner said no. Ringing the bell on one would let
  // the team raise a fresh approval for a bill that was already declined, so
  // the bell is put out of reach and says why.
  const chosen = tickets.find((t) => t.id === selected) ?? null;
  const closed = chosen ? chosen.status === "resolved" || chosen.status === "refused" : false;

  return (
    <aside className="rail">
      <div className="rail-head">
        <h2>On the spike</h2>
        <span className="count">{openCount} open</span>
      </div>

      <div className="slips">
        {tickets.map((ticket) => {
          const isSelected = ticket.id === selected;
          const settled = !ticket.is_open;
          return (
            <button
              key={ticket.id}
              className={[
                "slip",
                `k-${ticket.type}`,
                isSelected ? "selected" : "",
                settled ? "settled" : "",
                justResolved === ticket.id ? "fresh-stamp" : "",
              ].join(" ")}
              onClick={() => onSelect(ticket.id)}
              disabled={running}
            >
              <span className="slip-art">
                {ticket.sku
                  ? <ProductArt sku={ticket.sku} size={26} />
                  : <TicketTypeIcon type={ticket.type} size={24} />}
              </span>

              <div className="slip-body">
                <div className="slip-top">
                  <span className="slip-no">#{ticket.id}</span>
                  <span className={`slip-type t-${ticket.type}`}>
                    <TicketTypeIcon type={ticket.type} size={12} />
                    {TYPE_LABEL[ticket.type] ?? ticket.type}
                  </span>
                </div>

                <div className="slip-subject">{ticket.subject}</div>
                <div className="slip-from">{ticket.requester}</div>

                {ticket.sku && (
                  <div className="slip-line">
                    {ticket.qty} × <code>{ticket.sku}</code>
                    {ticket.size ? ` · size ${ticket.size}` : ""}
                  </div>
                )}
                {ticket.lease_id && <div className="slip-line">lease #{ticket.lease_id}</div>}

                <div className={`slip-status s-${ticket.status}`}>
                  {STATUS_LABEL[ticket.status] ?? ticket.status}
                </div>
              </div>

              {ticket.status === "waiting_on_vendor" && (
                <span className="van" aria-hidden><VanArt width={74} /></span>
              )}

              {(ticket.status === "resolved" || ticket.status === "refused") && (
                <span className={`stamp ${ticket.status === "resolved" ? "ok" : "hold"}`}>
                  {ticket.status === "resolved" ? "RESOLVED" : "REFUSED"}
                </span>
              )}
            </button>
          );
        })}

        {!tickets.length && <div className="empty">No tickets on the spike.</div>}
      </div>

      <button
        className="bell"
        onClick={onRun}
        disabled={running || selected === null || closed}
        title={
          closed
            ? `Ticket #${selected} is ${STATUS_LABEL[chosen!.status]?.toLowerCase()} and is not worked again. Reset the shop to start over.`
            : undefined
        }
      >
        {running ? (
          <>
            <span className="spinner" aria-hidden /> team working…
          </>
        ) : closed ? (
          <>
            <BellIcon size={22} />
            <span className="bell-stack">
              Ticket #{selected} is closed
              <span className="bell-sub">
                {chosen!.status === "refused"
                  ? "you declined this one — reset the shop to start over"
                  : "the shop is finished with it — reset the shop to start over"}
              </span>
            </span>
          </>
        ) : (
          <>
            <BellIcon size={22} />
            <span className="bell-stack">
              Ring the bell
              <span className="bell-sub">start the team on #{selected}</span>
            </span>
          </>
        )}
      </button>
    </aside>
  );
}
