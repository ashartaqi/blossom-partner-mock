import { Link } from "react-router-dom";

import { SIDEBAR_SECTIONS } from "./nav";

/** One rail entry. Renders an <a> for the cross-origin Investments link and a
 *  router <Link> for everything that stays inside this app. */
function NavItem({ item, active }) {
  const { icon: Glyph, label, to, href } = item;
  const className = `nav-item${active ? " is-active" : ""}`;
  const body = (
    <>
      <Glyph className="nav-icon" />
      <span className="nav-label">{label}</span>
    </>
  );

  if (href) {
    return (
      <a className={className} href={href}>
        {body}
      </a>
    );
  }
  return (
    <Link className={className} to={to} aria-current={active ? "page" : undefined}>
      {body}
    </Link>
  );
}

/** Desktop navigation rail. Collapses to icons only on narrow desktops, and is
 *  hidden entirely on mobile, where BottomNav takes over. */
export default function Sidebar({ activeId }) {
  return (
    <aside className="sidebar">
      <Link to="/dashboard" className="sidebar-brand" aria-label="Blossom home">
        <span className="brand-mark" aria-hidden="true">
          B
        </span>
        <span className="brand-word">Blossom</span>
      </Link>

      <nav className="sidebar-nav">
        {SIDEBAR_SECTIONS.map((section, i) => (
          <div className="nav-group" key={i}>
            {section.label && <p className="nav-group-label">{section.label}</p>}
            {section.items.map((item) => (
              <NavItem key={item.id} item={item} active={item.id === activeId} />
            ))}
          </div>
        ))}
      </nav>

      <p className="sidebar-footer">Partner platform · mock</p>
    </aside>
  );
}
