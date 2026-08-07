import { useEffect, useState } from "react";

import { api } from "../api";

const when = (value) =>
  new Date(typeof value === "number" ? value * 1000 : value).toLocaleTimeString();

/** Recent authorizations, newest first.
 *
 *  This is the view that turns a broken integration into an obvious one. A code
 *  issued with no token behind it means the client never reached /oauth/token —
 *  in practice always a wrong client secret or a redirect_uri that did not match
 *  the registration exactly. */
export default function ActivityPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    try {
      setData(await api.provider.activity());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="console-section">
      <div className="section-head">
        <div>
          <h2>Recent authorizations</h2>
          <p className="small">
            Codes issued at <code>/oauth/authorize</code>, and the tokens they
            were redeemed for. A code with no matching token means the client
            never completed the exchange.
          </p>
        </div>
        <button type="button" className="btn btn-quiet" onClick={load}>
          Refresh
        </button>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!data ? (
        <p className="muted small">Loading…</p>
      ) : (
        <>
          <div className="panel">
            <h3>Authorization codes</h3>
            {data.codes.length === 0 ? (
              <p className="muted small">
                None yet. Click Investments on the dashboard to create one.
              </p>
            ) : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Client</th>
                      <th>Member</th>
                      <th>PKCE</th>
                      <th>Issued</th>
                      <th>State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.codes.map((c, i) => (
                      <tr key={`${c.code_preview}-${i}`}>
                        <td>
                          <code>{c.code_preview}</code>
                        </td>
                        <td>{c.client_id}</td>
                        <td>{c.user}</td>
                        <td>{c.used_pkce ? "S256" : <span className="warn">none</span>}</td>
                        <td className="muted">{when(c.created_at)}</td>
                        <td>
                          {c.expired ? (
                            <span className="muted">spent / expired</span>
                          ) : (
                            <span className="live">live</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="panel">
            <h3>Access tokens</h3>
            {data.tokens.length === 0 ? (
              <p className="muted small">None yet.</p>
            ) : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Token</th>
                      <th>Client</th>
                      <th>Member</th>
                      <th>Scope</th>
                      <th>Issued</th>
                      <th>State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tokens.map((t, i) => (
                      <tr key={`${t.token_preview}-${i}`}>
                        <td>
                          <code>{t.token_preview}</code>
                        </td>
                        <td>{t.client_id}</td>
                        <td>{t.user}</td>
                        <td className="muted">{t.scope}</td>
                        <td className="muted">{when(t.issued_at)}</td>
                        <td>
                          {t.revoked ? (
                            <span className="muted">revoked</span>
                          ) : (
                            <span className="live">active</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted small">
              This token&rsquo;s only privilege is reading <code>/oauth/userinfo</code>.
              It is not a session on Blossom and it cannot move money — the worst a
              leaked one discloses is the profile of the member already being
              handed over.
            </p>
          </div>
        </>
      )}
    </section>
  );
}
