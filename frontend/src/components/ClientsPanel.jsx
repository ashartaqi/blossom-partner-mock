import { useEffect, useState } from "react";

import { api } from "../api";

const BLANK = {
  client_id: "",
  client_name: "",
  redirect_uris: "",
  post_logout_redirect_uris: "",
  scope: "openid profile email",
  is_trusted: true,
};

const toLines = (list) => (list ?? []).join("\n");
const fromLines = (text) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

/** Shown exactly once, when a secret is minted or rotated.
 *
 *  Only the SHA-256 digest is stored, so this is genuinely the sole moment the
 *  value exists anywhere outside the client's own configuration. Saying so
 *  matters — a developer who assumes they can come back for it later will not
 *  copy it now. */
function SecretOnce({ clientId, secret, onDismiss }) {
  return (
    <div className="secret-once">
      <div>
        <h3>Client secret for {clientId}</h3>
        <p>
          Copy it now. Only a hash is stored, so this cannot be shown again — it
          can only be replaced by rotating.
        </p>
        <code className="secret-value">{secret}</code>
      </div>
      <button type="button" className="btn btn-quiet" onClick={onDismiss}>
        Done
      </button>
    </div>
  );
}

function ClientRow({ client, onChanged, onSecret, onError }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function startEditing() {
    setDraft({
      client_name: client.client_name,
      redirect_uris: toLines(client.redirect_uris),
      post_logout_redirect_uris: toLines(client.post_logout_redirect_uris),
      scope: client.scope,
      is_trusted: client.is_trusted,
    });
  }

  async function run(action) {
    setBusy(true);
    onError(null);
    try {
      await action();
      await onChanged();
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="client">
      <button
        type="button"
        className="client-head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="client-title">
          <strong>{client.client_name}</strong>
          <code>{client.client_id}</code>
        </span>
        <span className="client-meta">
          {client.is_trusted && <span className="tag">first-party</span>}
          <span className="muted small">{client.authorizations ?? 0} authorizations</span>
          <span className="chevron">{open ? "▲" : "▼"}</span>
        </span>
      </button>

      {open && (
        <div className="client-body">
          {!draft ? (
            <>
              <dl>
                <dt>redirect_uris</dt>
                <dd>
                  {client.redirect_uris.map((u) => (
                    <div key={u}>
                      <code>{u}</code>
                    </div>
                  ))}
                  <span className="muted small">
                    Matched exactly — no wildcards, no prefixes. Loose matching
                    here is the most reliably exploited bug in OAuth deployments.
                  </span>
                </dd>
                <dt>post-logout redirect</dt>
                <dd>
                  {client.post_logout_redirect_uris.length ? (
                    client.post_logout_redirect_uris.map((u) => (
                      <div key={u}>
                        <code>{u}</code>
                      </div>
                    ))
                  ) : (
                    <span className="muted small">none</span>
                  )}
                </dd>
                <dt>scope</dt>
                <dd>
                  <code>{client.scope}</code>
                </dd>
                <dt>grant / response</dt>
                <dd>
                  <code>{client.grant_types.join(", ")}</code> ·{" "}
                  <code>{client.response_types.join(", ")}</code>
                </dd>
                <dt>token auth / signing</dt>
                <dd>
                  <code>{client.token_endpoint_auth_method}</code> ·{" "}
                  <code>{client.id_token_signed_response_alg}</code>
                </dd>
                <dt>consent screen</dt>
                <dd>
                  {client.is_trusted ? "Skipped" : "Shown"}
                  <span className="muted small">
                    {client.is_trusted
                      ? " — first-party, so the member is not asked to authorise Blossom to talk to Blossom."
                      : " — as for any third-party client."}
                  </span>
                </dd>
              </dl>

              <div className="client-actions">
                <button type="button" className="btn btn-quiet" onClick={startEditing}>
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-quiet"
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      const updated = await api.provider.rotateSecret(client.client_id);
                      onSecret({
                        clientId: client.client_id,
                        secret: updated.client_secret,
                      });
                    })
                  }
                >
                  Rotate secret
                </button>
                {confirmingDelete ? (
                  <span className="confirm">
                    <span className="small">Delete {client.client_id}?</span>
                    <button
                      type="button"
                      className="btn btn-danger"
                      disabled={busy}
                      onClick={() =>
                        run(() => api.provider.deleteClient(client.client_id))
                      }
                    >
                      Yes, delete
                    </button>
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => setConfirmingDelete(false)}
                    >
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="btn-link danger"
                    onClick={() => setConfirmingDelete(true)}
                  >
                    Delete
                  </button>
                )}
              </div>
            </>
          ) : (
            <form
              className="client-edit"
              onSubmit={(event) => {
                event.preventDefault();
                run(async () => {
                  await api.provider.updateClient(client.client_id, {
                    client_name: draft.client_name,
                    redirect_uris: fromLines(draft.redirect_uris),
                    post_logout_redirect_uris: fromLines(
                      draft.post_logout_redirect_uris
                    ),
                    scope: draft.scope,
                    is_trusted: draft.is_trusted,
                  });
                  setDraft(null);
                });
              }}
            >
              <label>
                Name
                <input
                  value={draft.client_name}
                  onChange={(e) => setDraft({ ...draft, client_name: e.target.value })}
                />
              </label>
              <label>
                Redirect URIs — one per line
                <textarea
                  rows={3}
                  value={draft.redirect_uris}
                  onChange={(e) => setDraft({ ...draft, redirect_uris: e.target.value })}
                />
              </label>
              <label>
                Post-logout redirect URIs — one per line
                <textarea
                  rows={2}
                  value={draft.post_logout_redirect_uris}
                  onChange={(e) =>
                    setDraft({ ...draft, post_logout_redirect_uris: e.target.value })
                  }
                />
              </label>
              <label>
                Scope
                <input
                  value={draft.scope}
                  onChange={(e) => setDraft({ ...draft, scope: e.target.value })}
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={draft.is_trusted}
                  onChange={(e) => setDraft({ ...draft, is_trusted: e.target.checked })}
                />
                First-party — skip the consent screen
              </label>

              <div className="client-actions">
                <button type="submit" className="btn" disabled={busy}>
                  {busy ? "Saving…" : "Save"}
                </button>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => setDraft(null)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

/** Register, inspect, edit and remove relying parties — the provider's core job. */
export default function ClientsPanel() {
  const [clients, setClients] = useState(null);
  const [error, setError] = useState(null);
  const [secret, setSecret] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [form, setForm] = useState(BLANK);
  const [busy, setBusy] = useState(false);

  async function load() {
    setClients(await api.provider.clients());
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function onRegister(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.provider.createClient({
        client_id: form.client_id.trim(),
        client_name: form.client_name.trim(),
        redirect_uris: fromLines(form.redirect_uris),
        post_logout_redirect_uris: fromLines(form.post_logout_redirect_uris),
        scope: form.scope,
        is_trusted: form.is_trusted,
      });
      setSecret({ clientId: created.client_id, secret: created.client_secret });
      setForm(BLANK);
      setRegistering(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="console-section">
      <div className="section-head">
        <div>
          <h2>Relying parties</h2>
          <p className="small">
            Onboarding an integration is one row and one secret. No code change,
            no deploy, no per-partner branch anywhere in the provider — which is
            the whole reason for using the standard.
          </p>
        </div>
        <button
          type="button"
          className="btn"
          onClick={() => setRegistering((v) => !v)}
        >
          {registering ? "Cancel" : "Register client"}
        </button>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {secret && (
        <SecretOnce
          clientId={secret.clientId}
          secret={secret.secret}
          onDismiss={() => setSecret(null)}
        />
      )}

      {registering && (
        <form className="panel client-edit" onSubmit={onRegister}>
          <label>
            client_id
            <input
              value={form.client_id}
              onChange={(e) => setForm({ ...form, client_id: e.target.value })}
              placeholder="surmount-blossom"
              required
              autoFocus
            />
          </label>
          <label>
            Display name
            <input
              value={form.client_name}
              onChange={(e) => setForm({ ...form, client_name: e.target.value })}
              placeholder="Surmount Investing"
            />
          </label>
          <label>
            Redirect URIs — one per line, absolute, matched exactly
            <textarea
              rows={3}
              value={form.redirect_uris}
              onChange={(e) => setForm({ ...form, redirect_uris: e.target.value })}
              placeholder="https://api.example.com/api/sso/callback/"
              required
            />
          </label>
          <label>
            Post-logout redirect URIs — one per line
            <textarea
              rows={2}
              value={form.post_logout_redirect_uris}
              onChange={(e) =>
                setForm({ ...form, post_logout_redirect_uris: e.target.value })
              }
            />
          </label>
          <label>
            Scope
            <input
              value={form.scope}
              onChange={(e) => setForm({ ...form, scope: e.target.value })}
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.is_trusted}
              onChange={(e) => setForm({ ...form, is_trusted: e.target.checked })}
            />
            First-party — skip the consent screen
          </label>

          <div className="client-actions">
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Registering…" : "Register"}
            </button>
          </div>
        </form>
      )}

      {clients === null ? (
        <p className="muted small">Loading…</p>
      ) : clients.length === 0 ? (
        <p className="muted small">
          No clients registered. Nothing can complete an authorization until one
          is.
        </p>
      ) : (
        <div className="client-list">
          {clients.map((client) => (
            <ClientRow
              key={client.client_id}
              client={client}
              onChanged={load}
              onSecret={setSecret}
              onError={setError}
            />
          ))}
        </div>
      )}
    </section>
  );
}
