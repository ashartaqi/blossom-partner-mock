import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import Avatar from "../components/Avatar";

export default function Profile() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="page">
      <header className="page-header">
        <h1>Profile</h1>
        <p>A second protected page — reachable only with a valid partner session.</p>
      </header>

      <section className="panel">
        <div className="profile-identity">
          <Avatar user={user} className="profile-avatar" />
          <div>
            <p className="profile-name">
              {user.first_name} {user.last_name}
            </p>
            <p className="muted small profile-email">{user.email}</p>
          </div>
        </div>

        <dl>
          <dt>Account ID</dt>
          <dd>
            <code>{user.id}</code>
          </dd>
          <dt>Picture</dt>
          <dd>
            <code>{user.picture}</code>
            <span className="muted small">
              {" "}
              — drawn once when the account was created. It does not change.
            </span>
          </dd>
          <dt>Member since</dt>
          <dd>{new Date(user.created_at).toLocaleString()}</dd>
        </dl>
      </section>

      {/* Also reachable from the topbar, but that is desktop-only — on a phone
          the rail and its sign-out are off-screen, and this is the only way out. */}
      <section className="panel sign-out-panel">
        <div>
          <h2>Sign out</h2>
          <p className="small">
            Ends both credentials: the token this app holds and the session cookie
            the hand-off relies on.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => {
            signOut();
            navigate("/signin", { replace: true });
          }}
        >
          Sign out
        </button>
      </section>
    </div>
  );
}
