# Blossom — the partner platform

A stand-in for Blossom's real banking platform, built so the sign-in hand-off into
Surmount can be developed and tested end to end before anyone at Blossom writes a
line of code.

It is also the reference implementation. The `backend/oidc/` app is a working
OpenID Provider, and it is roughly the amount of code standing one up actually
takes — about 400 lines, most of them answering questions about Blossom's own
data rather than implementing any protocol.

| | Runs on | What it is |
|---|---|---|
| `backend/` | `:9000` | Blossom's API **and** its OpenID Provider |
| `frontend/` | `:5300` | Blossom's web app — dashboard, accounts, provider console |

The other two halves live elsewhere:

| | Runs on | What it is |
|---|---|---|
| `../blossom-fe` | `:4001` | **Whitelabel** — the Blossom-branded investing app |
| `../backend` | `:8000` | **Surmount** — the real backend behind it |

### Who is who

**Blossom is the OpenID Provider.** It owns the members, their passwords and the
browser session, and it signs ID tokens with its own key.
**Surmount is the Relying Party.** It holds a `client_id` and `client_secret`,
starts the flow, and verifies what comes back.

Flow: **authorization code + PKCE (S256)**, confidential client.

---

## The Surmount side

The two halves of this integration that live in Surmount's own repositories, both
on branch **`feat/partner-sso-oidc`**:

| Repository | PR | Branch |
|---|---|---|
| `Surmount-AI/backend` | [#3124](https://github.com/Surmount-AI/backend/pull/3124) | `feat/partner-sso-oidc` |
| `Surmount-AI/blossom-fe` | [#90](https://github.com/Surmount-AI/blossom-fe/pull/90) | `feat/partner-sso-oidc` |

Check both out before running the full four-service flow:

```bash
cd ~/Projects/backend    && git checkout feat/partner-sso-oidc
cd ~/Projects/blossom-fe && git checkout feat/partner-sso-oidc
```

---

## Running it

### 1. Backend — `:9000`

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env          # then fill in the two shared secrets, below
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 9000
```

### 2. Frontend — `:5300`

```bash
cd frontend
npm install
cp .env.example .env          # defaults already point at :9000 and :8000
npm run dev
```

Open **http://localhost:5300**, create an account, and you land on a dashboard
with real balances and a working **Investments** link.

### 3. Register Surmount as a client

This is the whole of onboarding a partner — one row, one secret, no deploy:

```bash
cd backend
.venv/bin/python manage.py register_oidc_client \
  --client-id surmount-blossom \
  --name "Surmount Investing" \
  --redirect-uri http://localhost:8000/api/sso/blossom/callback/ \
  --post-logout-redirect-uri http://localhost:5300/dashboard \
  --trusted
```

The client secret is printed **once**. Only its SHA-256 digest is stored, so it
cannot be recovered — only replaced, with `--rotate-secret`. Put the printed
value into Surmount's `.env` as `SSO_CLIENT_SECRET`.

### 4. Give yourself the provider console

The console registers clients and rotates secrets, so it is staff-only. Members
sign in through this same app, which is exactly why it cannot just check that you
are signed in:

```bash
.venv/bin/python manage.py grant_console you@example.com
# or, for a throwaway local database:
.venv/bin/python manage.py grant_console --all
```

Then **Integration** appears in the sidebar under *For developers*.

---

## Environment

Nothing secret is committed. Both apps ship a `.env.example`; copy each to `.env`.

### `backend/.env`

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Django's own. Any long random string locally. |
| `DEBUG` | `True` locally. |
| `ALLOWED_HOSTS` | Comma-separated. |
| `CORS_ALLOWED_ORIGINS` | Must include `http://localhost:5300`. |
| `PUBLIC_BASE_URL` | The issuer. Must match exactly what Surmount is configured with — an issuer mismatch fails ID token validation. |
| `SSO_CLIENT_ID` / `SSO_CLIENT_SECRET` | Only for the legacy token-exchange fallback in `sso/`. **Must match Surmount's values exactly.** |

Generate a key with:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

### `frontend/.env`

Both values are non-secret and inlined into the bundle by Vite, so never put a
real secret here:

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | `http://localhost:9000` |
| `VITE_INVESTMENTS_URL` | `http://localhost:8000/api/sso/blossom/start/` — Surmount's URL, not Blossom's |

### Not in the repository, by design

| Path | Why |
|---|---|
| `backend/keys/` | The RSA signing key. Generated on first run at mode 0600. |
| `backend/db.sqlite3` | Member rows, password hashes, client secret hashes. |
| `*/.env` | Secrets and per-machine configuration. |

---

## What a member sees

Signup opens two real accounts and posts ninety days of history — salary on the
1st and 15th, everyday spending, a standing transfer into savings. Balances are
**derived by summing the ledger**, never stored independently, so the two cannot
disagree.

This is generated data, but it is generated once into the database and then read
back like any other platform's. No screen holds a hardcoded balance.

Every member also gets a profile picture at signup, from DiceBear — random style
and seed, written to the row, never recomputed. It travels to Surmount as the
OIDC `picture` claim.

---

## The provider console

`/developer` in the app, staff-only. Not a document about the configuration — a
view of the running one.

- **Overview** — live counts, every endpoint, the discovery URL to hand an integrator
- **Clients** — register, edit redirect URIs and scopes, rotate secrets, delete
- **Activity** — recent authorization codes and tokens, with the PKCE method used.
  A code with no token behind it means the client never reached `/oauth/token` —
  in practice always a wrong secret or a redirect URI that did not match exactly.
- **Reference** — your claims, the live discovery document, the JWKS

---

## Tests

```bash
cd backend && .venv/bin/python manage.py test oidc      # 33 tests
```

Mostly refusals: an unregistered redirect URI, a code redeemed twice, a PKCE
verifier that does not match, a client with the wrong secret.

---

## The flow, in one paragraph

A member signed into Blossom taps **Investments**. That is a plain link to
Surmount's `/api/sso/blossom/start/` — no API call, no JavaScript. Surmount
redirects the browser back to Blossom's `/oauth/authorize`, which sees the
member's session cookie and immediately redirects to Surmount's callback with a
short-lived code. Surmount trades that code server-to-server for a signed ID
token, verifies the signature against Blossom's published keys, and now knows who
the member is — without the member typing anything, and without Blossom ever
sharing a password.

Two visible redirects. Under a second. See `INTEGRATION.md` for the full
walk-through with payloads.

---

## Layout

```
backend/
  oidc/            The OpenID Provider
    keys.py        RSA signing key; public half published at /.well-known/jwks.json
    models.py      Client, authorization code, access token
    server.py      Authlib wiring — the entire protocol
    views.py       discovery, jwks, authorize, token, userinfo, login, logout
    console.py     The staff-only provider console API
    tests.py       33 tests, mostly rejections
  partner/         Members, avatars, Blossom's own API
  banking/         Accounts and transactions — what a member actually holds
  sso/             Token-exchange fallback, for a partner with no provider

frontend/
  src/pages/       Dashboard, Money, Profile, Developer, SignIn, SignUp
  src/components/  Shell, sidebar, topbar, account switcher, console panels
```

Authlib owns every protocol decision — request parsing, redirect-URI validation,
PKCE comparison, ID token signing, spec-shaped error responses. There is no
hand-rolled cryptography anywhere in this repository, which is the point: the
parts that are easy to get subtly and dangerously wrong are the parts nobody here
wrote.
