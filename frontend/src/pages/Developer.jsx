import { useEffect, useState } from "react";

import { api, BASE_HEADERS } from "../api";
import { useAuth } from "../auth";
import ActivityPanel from "../components/ActivityPanel";
import ClientsPanel from "../components/ClientsPanel";
import CopyField from "../components/CopyField";

/* Three tabs, one question each:
 *
 *   Integration — what do we send the team integrating with us?
 *   Clients     — who is registered, and what may they do?
 *   Activity    — is it actually working?
 *
 * They were four, and the split was wrong: "Overview" and "Reference" both held
 * pieces of the hand-over, so answering the first question meant visiting two
 * tabs and knowing which half lived where. */
const TABS = [
  { id: "integration", label: "Integration" },
  { id: "clients", label: "Clients" },
  { id: "activity", label: "Activity" },
];

function RawDoc({ title, url, data }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="panel">
      <div className="doc-head">
        <h3>{title}</h3>
        <span className="doc-actions">
          <button type="button" className="btn-link" onClick={() => setOpen((v) => !v)}>
            {open ? "Hide" : "Show"} JSON
          </button>
          {url && (
            <a className="doc-link" href={url} target="_blank" rel="noreferrer">
              Open raw ↗
            </a>
          )}
        </span>
      </div>
      {/* Collapsed by default. It is reference material, not something anyone
          needs on the way to copying the issuer URL. */}
      {open &&
        (data ? (
          <pre className="doc">{JSON.stringify(data, null, 2)}</pre>
        ) : (
          <p className="muted small">Loading…</p>
        ))}
    </div>
  );
}

/** Warns when the browser reached this console on a host the issuer does not
 *  name. That is the normal state five seconds after starting a tunnel, and the
 *  failure it causes lands on the other team as an unexplained rejected token. */
function IssuerMismatch({ overview }) {
  if (overview.issuer_matches_request !== false) return null;
  return (
    <div className="panel warning">
      <h3>The issuer does not match this address</h3>
      <p>
        You opened this console at <code>{overview.request_origin}</code>, but
        the issuer is set to <code>{overview.issuer}</code>. Every URL below, and
        the <code>iss</code> claim in every ID token, uses the issuer. A relying
        party will reject tokens that name an address it cannot reach.
      </p>
      <p className="small">
        Set this in <code>backend/.env</code> and restart:
      </p>
      <CopyField
        label="PUBLIC_BASE_URL"
        value={`PUBLIC_BASE_URL=${overview.request_origin}`}
      />
    </div>
  );
}

/** What the integrating team needs, in the order they need it. */
function Integration({ overview, discovery, jwks, claims }) {
  if (!overview) return <p className="muted small">Loading…</p>;
  const { endpoints } = overview;

  return (
    <section className="console-section">
      <IssuerMismatch overview={overview} />

      <div className="panel highlight">
        <h3>Send this to the integrating team</h3>
        <p>
          Just the issuer. Every endpoint, signing key and supported claim is
          read from the discovery document at that address, so nothing else has
          to be kept in step by hand.
        </p>
        <CopyField label="Issuer" value={overview.issuer} />
        <CopyField label="Discovery document" value={endpoints.discovery} />
      </div>

      <div className="panel">
        <h3>Endpoints</h3>
        <p className="small">
          Listed for reference. An integrator reads all of these from the
          discovery document rather than configuring them one by one.
        </p>
        <dl className="endpoints">
          <dt>Authorize</dt>
          <dd>
            <code>{endpoints.authorize}</code>
            <p className="muted small">
              A browser navigation. It reads the member&rsquo;s session cookie,
              which is why they are not asked to sign in twice.
            </p>
          </dd>
          <dt>Token</dt>
          <dd>
            <code>{endpoints.token}</code>
            <p className="muted small">Server to server. The client secret is required.</p>
          </dd>
          <dt>Userinfo</dt>
          <dd>
            <code>{endpoints.userinfo}</code>
          </dd>
          <dt>JWKS</dt>
          <dd>
            <code>{endpoints.jwks}</code>
            <p className="muted small">
              The public keys. An ID token whose signature is not checked against
              these is only a claim.
            </p>
          </dd>
          <dt>End session</dt>
          <dd>
            <code>{endpoints.end_session}</code>
          </dd>
        </dl>
      </div>

      <div className="panel">
        <h3>Claims they will receive</h3>
        <p className="small">
          Yours, built by the same function the token and userinfo endpoints
          call, so this cannot show one shape while the hand-off sends another.
        </p>
        {claims ? (
          <pre className="doc">{JSON.stringify(claims, null, 2)}</pre>
        ) : (
          <p className="muted small">Loading…</p>
        )}
        <p className="small">
          <strong>
            <code>sub</code> is the contract.
          </strong>{" "}
          It is stored and matched on forever, so it must be immutable and never
          reused. It is never matched on email, because addresses get changed and
          recycled, and a match on a recycled one would eventually hand a member
          someone else&rsquo;s account.
        </p>
      </div>

      <RawDoc
        title="Discovery document"
        url={endpoints.discovery}
        data={discovery}
      />
      <RawDoc title="Signing keys (JWKS)" url={endpoints.jwks} data={jwks} />
    </section>
  );
}

/**
 * The provider console.
 *
 * Not an integration guide with live values pasted in — the operator's view of a
 * running OpenID Provider.
 */
export default function Developer() {
  const { user } = useAuth();
  const [tab, setTab] = useState("integration");
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
        // Followed from the discovery document rather than a hardcoded path,
        // which is exactly how a relying party reaches it.
        const keys = await fetch(doc.jwks_uri, {
          headers: BASE_HEADERS,
        }).then((r) => r.json());
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
          <p>Operating the identity provider — integrations and their credentials.</p>
        </header>
        <section className="panel">
          <h2>You don&rsquo;t have access</h2>
          <p>
            The console can register clients and rotate secrets, so it is
            staff-only. Members sign in through this same app, which is exactly
            why it cannot just check that you are signed in.
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

      {tab === "integration" && (
        <Integration
          overview={overview}
          discovery={discovery}
          jwks={jwks}
          claims={claims}
        />
      )}
      {tab === "clients" && <ClientsPanel />}
      {tab === "activity" && <ActivityPanel />}
    </div>
  );
}
