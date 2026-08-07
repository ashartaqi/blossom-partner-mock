import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import AccountSwitcher from "./AccountSwitcher";
import Avatar from "./Avatar";
import { IconBell, IconSearch, IconSettings, IconSignOut } from "./icons";

/** Desktop header: account pill on the left, a tools pill on the right holding
 *  the icon actions and the member's picture. */
export default function Topbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <AccountSwitcher />

        <div className="tools-pill">
          <button type="button" className="tool" aria-label="Settings">
            <IconSettings />
          </button>
          <button type="button" className="tool" aria-label="Search">
            <IconSearch />
          </button>
          <button type="button" className="tool has-badge" aria-label="Notifications">
            <IconBell />
          </button>
          <button
            type="button"
            className="tool"
            aria-label="Sign out"
            onClick={() => {
              signOut();
              navigate("/signin", { replace: true });
            }}
          >
            <IconSignOut />
          </button>

          <Avatar user={user} className="tool-avatar" />
        </div>
      </div>
    </header>
  );
}
