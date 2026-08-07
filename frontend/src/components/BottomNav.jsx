import { Link } from "react-router-dom";

import { BOTTOM_NAV_ITEMS } from "./nav";

/** Mobile navigation. Replaces the rail below the desktop breakpoint. */
export default function BottomNav({ activeId }) {
  return (
    <nav className="bottom-nav">
      {BOTTOM_NAV_ITEMS.map((item) => {
        const { icon: Glyph, label, to, href, id } = item;
        const className = `bottom-item${id === activeId ? " is-active" : ""}`;
        const body = (
          <>
            <Glyph className="bottom-icon" />
            <span>{label}</span>
          </>
        );
        return href ? (
          <a key={id} className={className} href={href}>
            {body}
          </a>
        ) : (
          <Link key={id} className={className} to={to}>
            {body}
          </Link>
        );
      })}
    </nav>
  );
}
