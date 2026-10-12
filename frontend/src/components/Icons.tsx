/** Inline SVG art for the desk.
 *
 * Everything is drawn here rather than loaded from a file or a CDN, so the
 * dashboard stays self-contained and crisp at any size. Shapes use
 * `currentColor` so they inherit each agent's or each state's colour.
 */

type P = { size?: number; className?: string };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

/* ------------------------------------------------------------- products */

export function TeeArt({ size = 34 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M8.5 3 5 5 3 9l3 1.5V21h12v-10.5L21 9l-2-4-3.5-2" />
      <path d="M8.5 3a3.5 3.5 0 0 0 7 0" />
    </svg>
  );
}

export function HoodieArt({ size = 34 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M8 3.5 4.5 5.5 2.5 10l3 1.4V21h13v-9.6l3-1.4-2-4.5L16 3.5" />
      <path d="M8 3.5c0 2.2 1.8 3.6 4 3.6s4-1.4 4-3.6" />
      <path d="M12 7.1V13" />
      <path d="M10.4 13h3.2" />
    </svg>
  );
}

export function CapArt({ size = 34 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M4 15a8 8 0 0 1 16 0" />
      <path d="M20 15h1.5a1.5 1.5 0 0 1 0 3H4a1.5 1.5 0 0 1 0-3h16Z" />
      <path d="M12 7v8" />
    </svg>
  );
}

export function MugArt({ size = 34 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M4 7h12v9a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V7Z" />
      <path d="M16 10h2.5a2.5 2.5 0 0 1 0 5H16" />
      <path d="M8 3.5v1.8M12 3v2.3" />
    </svg>
  );
}

/** Pick the right garment for a SKU. */
export function ProductArt({ sku, size = 34 }: { sku: string | null; size?: number }) {
  if (!sku) return null;
  if (sku.includes("TEE")) return <TeeArt size={size} />;
  if (sku.includes("HOOD")) return <HoodieArt size={size} />;
  if (sku.includes("HAT")) return <CapArt size={size} />;
  if (sku.includes("MUG")) return <MugArt size={size} />;
  return <TeeArt size={size} />;
}

/* ---------------------------------------------------------- ticket kinds */

export function BagIcon({ size = 18 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M4 7h16l-1.2 13.2a1 1 0 0 1-1 .8H6.2a1 1 0 0 1-1-.8L4 7Z" />
      <path d="M8.5 10V6.5a3.5 3.5 0 0 1 7 0V10" />
    </svg>
  );
}

export function KeyIcon({ size = 18 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <circle cx="8" cy="8" r="4" />
      <path d="M11 11l9 9M17.5 17.5l2-2M15 15l2-2" />
    </svg>
  );
}

export function TagIcon({ size = 18 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M3.5 11.8V4.5a1 1 0 0 1 1-1h7.3a1 1 0 0 1 .7.3l8 8a1 1 0 0 1 0 1.4l-7.3 7.3a1 1 0 0 1-1.4 0l-8-8a1 1 0 0 1-.3-.7Z" />
      <circle cx="7.8" cy="7.8" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function TicketTypeIcon({ type, size = 18 }: { type: string; size?: number }) {
  if (type === "rent_notice") return <KeyIcon size={size} />;
  if (type === "price_override") return <TagIcon size={size} />;
  return <BagIcon size={size} />;
}

/* ---------------------------------------------------------- agent badges */

export function BossIcon({ size = 22 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M3 8.5 7 12l5-7.5L17 12l4-3.5-1.6 9.5a1 1 0 0 1-1 .8H5.6a1 1 0 0 1-1-.8L3 8.5Z" />
    </svg>
  );
}

export function BoxIcon({ size = 22 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M12 2.8 21 7v10l-9 4.2L3 17V7l9-4.2Z" />
      <path d="M3 7l9 4.2L21 7M12 11.2V21.2" />
    </svg>
  );
}

export function CoinsIcon({ size = 22 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <ellipse cx="9" cy="6.5" rx="6" ry="2.8" />
      <path d="M3 6.5v4c0 1.5 2.7 2.8 6 2.8s6-1.3 6-2.8v-4" />
      <path d="M15 11.2c3.3 0 6 1.3 6 2.8v3.5c0 1.6-2.7 2.8-6 2.8s-6-1.2-6-2.8v-3.4" />
    </svg>
  );
}

export function BuildingIcon({ size = 22 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M4 21V5.5a1 1 0 0 1 .6-.9l7-3a1 1 0 0 1 1.4.9V21" />
      <path d="M13 10h6a1 1 0 0 1 1 1v10M3 21h18" />
      <path d="M7 8.5h2M7 12h2M7 15.5h2M16 14h1M16 17.5h1" />
    </svg>
  );
}

export function ChatIcon({ size = 22 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M21 12.5a7.5 7.5 0 0 1-7.5 7.5H7l-4 3v-4.6A7.5 7.5 0 0 1 3 12.5 7.5 7.5 0 0 1 10.5 5h3A7.5 7.5 0 0 1 21 12.5Z" />
      <path d="M8.5 11.5h7M8.5 15h4" />
    </svg>
  );
}

export function AgentIcon({ role, size = 22 }: { role: string; size?: number }) {
  switch (role) {
    case "boss": return <BossIcon size={size} />;
    case "inventory": return <BoxIcon size={size} />;
    case "accounting": return <CoinsIcon size={size} />;
    case "facilities": return <BuildingIcon size={size} />;
    case "customer_service": return <ChatIcon size={size} />;
    default: return <BossIcon size={size} />;
  }
}

/* ------------------------------------------------------------- the desk */

export function BellIcon({ size = 20 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M3.5 18h17a8.5 8.5 0 0 0-17 0Z" />
      <path d="M2 21h20M12 5.2V3.4" />
      <circle cx="12" cy="2.6" r="1.1" />
    </svg>
  );
}

export function PenIcon({ size = 16 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M15.5 4.5 19.5 8.5 8 20H4v-4L15.5 4.5Z" />
      <path d="M14 6l4 4" />
    </svg>
  );
}

export function StampIcon({ size = 16 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M6 20.5h12M5 17h14v-1.5a3 3 0 0 0-3-3h-1l.8-5A2.6 2.6 0 0 0 13.2 4.5h-2.4A2.6 2.6 0 0 0 8.2 7.5l.8 5H8a3 3 0 0 0-3 3V17Z" />
    </svg>
  );
}

export function ClockIcon({ size = 15 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.2l3.2 2" />
    </svg>
  );
}

export function TruckIcon({ size = 15 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M2 6.5h11v10H2zM13 10h4l3 3.2v3.3h-7" />
      <circle cx="6" cy="18" r="1.8" /><circle cx="17" cy="18" r="1.8" />
    </svg>
  );
}

export function CheckIcon({ size = 15 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M4 12.5 9.5 18 20 6.5" />
    </svg>
  );
}

export function WarnIcon({ size = 15 }: P) {
  return (
    <svg {...base(size)} aria-hidden>
      <path d="M12 3.5 22 20H2L12 3.5Z" />
      <path d="M12 10v4.2M12 17.2v.1" />
    </svg>
  );
}

export function ToolIcon({ size = 13 }: P) {
  return (
    <svg {...base(size)} strokeWidth={1.8} aria-hidden>
      <path d="M14.5 6a4 4 0 0 1-5.3 5.3L4 16.5 7.5 20l5.2-5.2A4 4 0 0 1 18 9.5l-2.6-1-0.9-2.5Z" />
    </svg>
  );
}

/* -------------------------------------------------------------- storefront */

/** The shop itself, for the masthead and the empty floor. */
export function Storefront({ width = 180 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 200 120" fill="none" aria-hidden>
      <defs>
        <linearGradient id="awn" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent-2)" />
          <stop offset="100%" stopColor="var(--accent)" />
        </linearGradient>
        <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--glass-a)" />
          <stop offset="100%" stopColor="var(--glass-b)" />
        </linearGradient>
      </defs>

      {/* building */}
      <rect x="18" y="30" width="164" height="78" rx="4" fill="var(--panel-2)" />
      {/* windows */}
      <rect x="30" y="52" width="58" height="40" rx="3" fill="url(#glass)" />
      <rect x="112" y="52" width="58" height="40" rx="3" fill="url(#glass)" />
      {/* door */}
      <rect x="92" y="62" width="16" height="46" rx="2" fill="var(--panel-3)" />
      <circle cx="104" cy="86" r="1.6" fill="var(--accent-2)" />
      {/* awning */}
      <path d="M12 30h176l-10 20H22L12 30Z" fill="url(#awn)" />
      <path d="M22 50h156" stroke="var(--panel)" strokeWidth="1.5" opacity=".35" />
      {/* scallops */}
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
        <circle key={i} cx={28 + i * 21} cy="50" r="4.5" fill="var(--accent)" opacity=".9" />
      ))}
      {/* sign */}
      <rect x="62" y="12" width="76" height="16" rx="8" fill="var(--panel-3)" />
      <text
        x="100" y="24" textAnchor="middle"
        fontFamily="Fraunces, Georgia, serif" fontSize="11" fontWeight="700"
        fill="var(--accent-2)"
      >
        CAMPUS CUSTOMS
      </text>
      {/* hanging tee in the left window */}
      <g stroke="var(--accent-2)" strokeWidth="1.4" fill="none" opacity=".75">
        <path d="M50 62l-5 3-2 5 4 2v12h14V72l4-2-2-5-5-3" />
        <path d="M50 62a4 4 0 0 0 8 0" />
      </g>
      {/* mug in the right window */}
      <g stroke="var(--accent-2)" strokeWidth="1.4" fill="none" opacity=".75">
        <path d="M128 70h14v11a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5V70Z" />
        <path d="M142 74h3a3 3 0 0 1 0 6h-3" />
      </g>
      {/* pavement */}
      <path d="M6 108h188" stroke="var(--panel-3)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** Small mark for the masthead. */
export function Crest({ size = 44 }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <defs>
        <linearGradient id="crestg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--accent-2)" />
          <stop offset="100%" stopColor="var(--accent)" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="13" fill="url(#crestg)" />
      <path
        d="M14 17l-3 2.2-1.4 3.4 2.4 1.2V34h12V23.8l2.4-1.2L25 19.2 22 17"
        stroke="var(--ink-on-accent)" strokeWidth="2" fill="none"
        strokeLinecap="round" strokeLinejoin="round"
      />
      <path d="M14 17a4 4 0 0 0 8 0" stroke="var(--ink-on-accent)" strokeWidth="2" fill="none"
        strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="34" cy="31" r="7.5" fill="var(--ink-on-accent)" opacity=".92" />
      <path d="M34 26.5v9M31.5 29h5M31.5 33h5" stroke="var(--accent)" strokeWidth="1.8"
        strokeLinecap="round" />
    </svg>
  );
}

/* ------------------------------------------------------------- portraits */

/** A small character portrait per agent, so the desks are staffed by people
 *  rather than by letters. Each one shares a silhouette and differs by hair
 *  and by the prop of their trade. `--ink` tints them to the agent's hue. */
export function AgentPortrait({ role, size = 40 }: { role: string; size?: number }) {
  const prop = () => {
    switch (role) {
      case "boss": // clipboard
        return (
          <g>
            <rect x="25" y="26" width="11" height="14" rx="1.5" fill="currentColor" opacity=".9" />
            <rect x="28" y="24" width="5" height="3" rx="1" fill="currentColor" />
            <path d="M27.5 31h6M27.5 34h6" stroke="var(--portrait-bg)" strokeWidth="1.2" strokeLinecap="round" />
          </g>
        );
      case "inventory": // crate
        return (
          <g>
            <path d="M25 29l6-3 6 3v7l-6 3-6-3v-7Z" fill="currentColor" opacity=".9" />
            <path d="M25 29l6 3 6-3M31 32v7" stroke="var(--portrait-bg)" strokeWidth="1.1" />
          </g>
        );
      case "accounting": // coin
        return (
          <g>
            <circle cx="31" cy="32" r="6.5" fill="currentColor" opacity=".9" />
            <path d="M31 28v8M28.8 30h4.4M28.8 34h4.4" stroke="var(--portrait-bg)" strokeWidth="1.3" strokeLinecap="round" />
          </g>
        );
      case "facilities": // key
        return (
          <g>
            <circle cx="28" cy="30" r="4" fill="none" stroke="currentColor" strokeWidth="2.2" />
            <path d="M31 33l6 6M35 37l2-2" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </g>
        );
      default: // headset
        return (
          <g>
            <path d="M24 33v-3a7 7 0 0 1 14 0v3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <rect x="22" y="32" width="4" height="6" rx="2" fill="currentColor" />
            <rect x="36" y="32" width="4" height="6" rx="2" fill="currentColor" />
          </g>
        );
    }
  };

  const hair = () => {
    switch (role) {
      case "boss":
        return <path d="M7 20a9 9 0 0 1 18 0c0 1-1 1.5-2 1-2-1.2-4-1.8-7-1.8s-5 .6-7 1.8c-1 .5-2 0-2-1Z" fill="currentColor" />;
      case "inventory":
        return <path d="M7 20c0-5 4-9 9-9s9 4 9 9c0 1.4-1.6 1-2.4.2-1.6-1.6-3.6-2.4-6.6-2.4-2 0-3.4.4-4.6 1.2-1.4.9-2 2.6-3 2.6-.8 0-1.4-.6-1.4-1.6Z" fill="currentColor" />;
      case "accounting":
        return <path d="M6.5 21c0-5.5 4.2-10 9.5-10s9.5 4.5 9.5 10c0 1.2-1.2 1.2-1.8.3-.6-1-.9-2.4-1.6-3-1.4 1-4 1.5-6.1 1.5-2.6 0-5-.6-6.6-1.8-.8.8-1.1 2.3-1.6 3.2-.5.9-1.3.9-1.3-.2Z" fill="currentColor" />;
      case "facilities":
        return <path d="M6 19.5C6 14 10.5 10 16 10s10 4 10 9.5c0 1.5-1.5 1.5-2.5.5-2-2-4.4-2.8-7.5-2.8s-5.5.8-7.5 2.8c-1 1-2.5 1-2.5-.5Z" fill="currentColor" />;
      default:
        return <path d="M7 21c0-5.5 4-10 9-10s9 4.5 9 10c0 1.3-1.3 1.3-2 .4-.5-3-2.4-5-7-5s-6.5 2-7 5c-.7.9-2 .9-2-.4Z" fill="currentColor" />;
    }
  };

  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden>
      <circle cx="24" cy="24" r="23" fill="var(--portrait-bg)" />
      {/* shoulders */}
      <path d="M6 47c0-8.5 7.5-13 18-13s18 4.5 18 13" fill="currentColor" opacity=".32" />
      {/* head */}
      <circle cx="16" cy="23" r="9" fill="currentColor" opacity=".55" />
      {hair()}
      {prop()}
    </svg>
  );
}

/* --------------------------------------------------------- empty states */

/** Shown when nothing is waiting on a signature. */
export function AllClearArt({ width = 120 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 120 80" fill="none" aria-hidden>
      <rect x="28" y="14" width="64" height="56" rx="6" fill="var(--panel-2)" stroke="var(--line)" />
      <rect x="46" y="8" width="28" height="12" rx="5" fill="var(--panel-3)" stroke="var(--line)" />
      <path d="M40 34h40M40 44h30M40 54h22" stroke="var(--line)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="88" cy="56" r="15" fill="var(--panel)" stroke="var(--mint)" strokeWidth="2" />
      <path d="M81 56.5l5 5 10-11" stroke="var(--mint)" strokeWidth="3"
        strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

/** A big hero for whichever ticket is selected. */
export function TicketHero({ sku, type, width = 150 }: { sku: string | null; type: string; width?: number }) {
  return (
    <div className="hero-art" style={{ width }}>
      <svg viewBox="0 0 150 110" width={width} fill="none" aria-hidden>
        <defs>
          <radialGradient id="heroglow" cx="50%" cy="42%" r="58%">
            <stop offset="0%" stopColor="currentColor" stopOpacity=".26" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="75" cy="48" r="46" fill="url(#heroglow)" />
        <ellipse cx="75" cy="97" rx="40" ry="6" fill="currentColor" opacity=".12" />
      </svg>
      <span className="hero-item">
        {sku ? <ProductArt sku={sku} size={66} /> : <TicketTypeIcon type={type} size={58} />}
      </span>
    </div>
  );
}

/* ------------------------------------------------------ desk watermarks */

/** A large, very faint drawing behind each agent's card, giving every desk its
 *  own texture: the Boss's bell, Inventory's shelf, Accounting's coin stack,
 *  the Facilities shopfront, Customer Service's letters. */
export function DeskWatermark({ role }: { role: string }) {
  const art = () => {
    switch (role) {
      case "boss":
        return (
          <g>
            <path d="M8 66h84a42 42 0 0 0-84 0Z" />
            <path d="M2 74h96M50 24v-8" />
            <circle cx="50" cy="11" r="5" />
          </g>
        );
      case "inventory":
        return (
          <g>
            <path d="M6 24h88M6 52h88M6 80h88" />
            <path d="M14 24V12h20v12M46 24V8h20v16M62 52V36h22v16M18 52V38h20v14M30 80V64h24v16" />
          </g>
        );
      case "accounting":
        return (
          <g>
            <ellipse cx="50" cy="20" rx="30" ry="9" />
            <path d="M20 20v12c0 5 13 9 30 9s30-4 30-9V20" />
            <path d="M20 44v12c0 5 13 9 30 9s30-4 30-9V44" />
            <path d="M20 68v8c0 5 13 9 30 9s30-4 30-9v-8" />
          </g>
        );
      case "facilities":
        return (
          <g>
            <path d="M10 84V30l40-18 40 18v54" />
            <path d="M2 84h96" />
            <rect x="24" y="42" width="16" height="14" />
            <rect x="60" y="42" width="16" height="14" />
            <path d="M40 84V62h20v22" />
          </g>
        );
      default:
        return (
          <g>
            <rect x="8" y="20" width="60" height="40" rx="4" />
            <path d="M8 24l30 22 30-22" />
            <rect x="34" y="44" width="58" height="38" rx="4" />
            <path d="M34 48l29 21 29-21" />
          </g>
        );
    }
  };

  return (
    <svg
      className="watermark"
      viewBox="0 0 100 92"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {art()}
    </svg>
  );
}

/* ------------------------------------------------------------- vignettes */

/** A van, for anything waiting on a vendor. */
export function VanArt({ width = 86 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 110 60" fill="none" aria-hidden>
      <path d="M4 14h56v30H4zM60 24h18l14 12v8H60" fill="var(--panel-2)" stroke="currentColor" strokeWidth="2.2"
        strokeLinejoin="round" />
      <path d="M64 28h10l7 6h-17z" fill="currentColor" opacity=".35" />
      <circle cx="22" cy="46" r="7" fill="var(--panel)" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="78" cy="46" r="7" fill="var(--panel)" stroke="currentColor" strokeWidth="2.2" />
      <path d="M12 22h26M12 30h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".55" />
      {/* motion lines */}
      <path d="M100 20h8M96 28h12M100 36h8" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" opacity=".4" />
    </svg>
  );
}

/** A ledger book, for the closing note. */
export function LedgerArt({ width = 52 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 60 50" fill="none" aria-hidden>
      <path d="M6 8a4 4 0 0 1 4-4h18v42H10a4 4 0 0 1-4-4V8Z" fill="var(--panel-2)"
        stroke="currentColor" strokeWidth="2" />
      <path d="M54 8a4 4 0 0 0-4-4H32v42h18a4 4 0 0 0 4-4V8Z" fill="var(--panel-2)"
        stroke="currentColor" strokeWidth="2" />
      <path d="M30 4v42" stroke="currentColor" strokeWidth="2" />
      <path d="M12 16h12M12 23h12M12 30h8M36 16h12M36 23h12M36 30h8" stroke="currentColor"
        strokeWidth="1.6" strokeLinecap="round" opacity=".6" />
    </svg>
  );
}

/** A torn receipt, to cap the tape view. */
export function ReceiptEnd({ width = 120 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 120 22" fill="none" aria-hidden>
      <path
        d="M0 2h120v8l-6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4 -6 4 -6-4V2Z"
        fill="var(--panel-2)" stroke="var(--line)" strokeWidth="1"
      />
    </svg>
  );
}
