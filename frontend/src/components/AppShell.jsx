import { useLocation } from "react-router-dom";

import BottomNav from "./BottomNav";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

/** Chrome shared by every signed-in page: rail, header, scrolling content, and
 *  the mobile bar. One definition, so the pages hold only their own content. */
export default function AppShell({ children }) {
  const { pathname } = useLocation();
  // Longest-prefix match, so a nested route still lights its section.
  const SECTIONS = ["money", "profile", "developer"];
  const activeId =
    SECTIONS.find((id) => pathname.startsWith(`/${id}`)) ?? "dashboard";

  return (
    <div className="shell">
      <Sidebar activeId={activeId} />
      <div className="shell-main">
        <Topbar />
        <main className="shell-content">{children}</main>
        <BottomNav activeId={activeId} />
      </div>
    </div>
  );
}
