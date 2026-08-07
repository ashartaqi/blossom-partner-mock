import { useEffect, useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import ActivityPanel from "../components/ActivityPanel";
import ClientsPanel from "../components/ClientsPanel";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "clients", label: "Clients" },
  { id: "activity", label: "Activity" },
  { id: "reference", label: "Reference" },
];

function Doc({ title, url, data }) {
  return (
    <div className="panel">
      <div className="doc-head">
        <h3>{title}</h3>
        {url && (
          <a className="doc-link" href={url} target="_blank" rel="noreferrer">
            Open raw ↗
          </a>
        )}
      </div>
      {data ? (
        <pre className="doc">{JSON.stringify(data, null, 2)}</pre>
      ) : (
        <p className="muted small">Loading…</p>
      )}
    </div>
  );
}

function Stat({ label, value, note }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      {note && <span className="stat-note">{note}</span>}
    </div>
  );
}

function Overview({ overview }) {
  if (!overview) return <p className="muted small">Loading…</p>;
  const { endpoints, stats } = overview;

  return (
    <section className="console-section">
      <div className="stat-row">
        <Stat label="Clients" value={stats.clients} />
        <Stat label="Codes issued" value={stats.codes_issued} />
        <Stat
          label="Codes live"
          value={stats.codes_live}
          note="60s each — near zero is normal"
        />
        <Stat label="Tokens issued" value={stats.tokens_issued} />
        <Stat label="Tokens active" value={stats.tokens_active} />
      </div>

      <div className="panel highlight">
        <h3>Give an integrator one URL</h3>
        <p>
          Every endpoint, signing key and supported claim is discovered from the
          document below, so nothing else has to be kept in step by hand.
        </p>
        <code className="wide-code">{endpoints.discovery}</code>
      </div>

      <div className="panel">
        <h3>Endpoints</h3>
        <dl>
          <dt>Issuer</dt>
          <dd>
            <code>{overview.issuer}</code>
          </dd>
          <dt>Authorize</dt>
          <dd>
            <code>{endpoints.authorize}</code>
            <span className="muted small">
              {" "}
              — a top-level navigation. Reads the member&rsquo;s session cookie,
              which is why they are not asked to sign in twice.
            </span>
          </dd>
          <dt>Token</dt>
          <dd>
            <code>{endpoints.token}</code>
            <span className="muted small"> — server-to-server, client secret required.</span>
          </dd>
          <dt>Userinfo</dt>
          <dd>
            <code>{endpoints.userinfo}</code>
          </dd>
          <dt>JWKS</dt>
          <dd>
            <code>{endpoints.jwks}</code>
            <span className="muted small">
              {" "}
              — public keys. An ID token whose signature is not verified against
              these is just a claim.
            </span>
          </dd>
          <dt>End session</dt>
          <dd>
            <code>{endpoints.end_session}</code>
          </dd>
        </dl>
      </div>
    </section>
  );
}

function Reference({ discovery, jwks, claims }) {
  return (
    <section className="console-section">
      <div className="panel">
        <h3>Claims for your account</h3>
        <p className="small">
          Produced by the same method the token endpoint calls, so this cannot
          advertise one thing while the hand-off sends another.
        </p>
        {claims ? (
          <pre className="doc">{JSON.stringify(claims, null, 2)}</pre>
        ) : (
          <p className="muted small">Loading…</p>
        )}
        <p className="small">
          <strong>
            <code>external_user_id</code> is the one hard requirement.
          </strong>{" "}
          It is stored and matched on forever, so it must be immutable and never
          reused. Never matched on email: addresses get changed and recycled, and
          a match against a recycled one would eventually hand a member someone
          else&rsquo;s brokerage account.
        </p>
      </div>

      <Doc title="Discovery document" data={discovery} url={discovery?.issuer && `${discovery.issuer}/.well-known/openid-configuration`} />
      <Doc title="Signing keys (JWKS)" data={jwks} url={discovery?.jwks_uri} />
    </section>
  );
}

/** The provider console.
 *
 *  Not an integration guide with live values pasted in — the operator's view of
 *  a running OpenID Provider. Register a relying party, edit what it is allowed
 *  to do, rotate its credential, and watch authorizations actually flowing. */
export default function Developer() {
  const { user } = useAuth();
  const [tab, setTab] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [discovery, setDiscovery] = useState(null);
  const [jwks, setJwks] = useState(null);
  const [claims, setClaims] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user?.is_staff) return undefined;
    let cancelled = false;

    (async () => {
      try {
        const [ov, doc, integration] = await Promise.all([
          api.provider.overview(),
          api.discovery(),
          api.integration(),
        ]);
        if (cancelled) return;
        setOverview(ov);
        setDiscovery(doc);
        setClaims(integration.claims_for_you);
        // Followed from the discovery document rather than a hardcoded path —
        // exactly how a relying party reaches it.
        const keys = await fetch(doc.jwks_uri).then((r) => r.json());
        if (!cancelled) setJwks(keys);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user]);

  if (!user?.is_staff) {
    return (
      <div className="page">
        <header className="page-header">
          <h1>Provider console</h1>
          <p>Operating the identity provider — registering integrations and their credentials.</p>
        </header>
        <section className="panel">
          <h2>You don&rsquo;t have access</h2>
          <p>
            The console can register clients and rotate secrets, so it is
            staff-only. Members sign in through this same app, which is exactly
            why it cannot just check that you are logged in.
          </p>
          <p className="small">
            Grant it locally with:{" "}
            <code>manage.py grant_console {user?.email ?? "you@example.com"}</code>
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Provider console</h1>
        <p>
          Blossom as an OpenID Provider. Everything here reads and writes the
          running configuration — there is no copy of it to go stale.
        </p>
      </header>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab${tab === t.id ? " is-active" : ""}`}
            onClick={() => setTab(t.id)}
            aria-current={tab === t.id ? "page" : undefined}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <Overview overview={overview} />}
      {tab === "clients" && <ClientsPanel />}
      {tab === "activity" && <ActivityPanel />}
      {tab === "reference" && (
        <Reference discovery={discovery} jwks={jwks} claims={claims} />
      )}
    </div>
  );
}
