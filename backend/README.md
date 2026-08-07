# BE1 — Blossom platform backend (mock)

A stand-in for the real Blossom platform backend, so the SSO hand-off into Surmount can
be built and tested end to end. **The `sso/` app is the reference implementation** the
Blossom developers should mirror; everything in `partner/` is throwaway scaffolding that
just gives us real users to test with.

Runs on **:9000**.

## Run

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in the secrets
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 9000
```

## Endpoints

### Scaffolding (mock only — Blossom already has its own equivalents)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/signup/` | — | Create a partner user, return JWT |
| POST | `/api/auth/login/` | — | Return JWT |
| POST | `/api/auth/refresh/` | — | Refresh the access token |
| GET | `/api/auth/me/` | Bearer | Protected — proves the token works |

### The SSO hand-off (this is what Blossom must build)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/sso/initiate/` | Bearer (the logged-in partner user) | Mint a one-time code, return `{ redirect_url }` |
| POST | `/sso/exchange/` | `client_id` + `client_secret` | Back-channel: burn the code, return the identity |

```
FE1 ──▶ POST /sso/initiate  ──▶ { "redirect_url": "http://localhost:4001/sso/callback?code=…" }
        browser follows it

BE2 ──▶ POST /sso/exchange  { code, client_id, client_secret }
                            ──▶ { external_user_id, email, first_name, last_name }
```

## Why it's built this way

- **`external_user_id` is the UUID primary key** of `PartnerUser` — immutable and never
  reused. Surmount matches on it forever. Matching on email instead would be a bug:
  emails get changed and recycled, and a match against a recycled email would hand one
  person another person's brokerage account.
- **The browser only ever holds the opaque code.** Identity travels once,
  server-to-server, over `/sso/exchange`. Nothing sensitive is ever in a URL.
- **The code is 256 bits, lives 60 seconds, and redeems exactly once.** The burn is a
  single conditional `UPDATE ... WHERE used_at IS NULL`, so two concurrent redemptions
  cannot both succeed.
- **Client credentials are compared with `hmac.compare_digest`.** A plain `==` would leak
  the secret a byte at a time to anyone who can measure latency, and this endpoint is the
  only door to every user's identity.
- **`redirect_uri` is an exact-match allow-list.** Without it, `/sso/initiate` is an open
  redirect that hands a valid identity code to any host the caller names.
- **Claims are snapshotted at mint time**, so a redemption reflects who the user was when
  they clicked — not who they were edited into during the 60-second window.
- **Rejections are deliberately indistinguishable** to the caller ("Invalid or expired
  code"). The specific reason — unknown / already-used / expired — goes to the audit log
  only, so a prober can't map out which codes ever existed.

## Verified behaviour

| Case | Expected | Result |
|---|---|---|
| Signup → JWT → `/me` | 200 | pass |
| `/me` with no token | 401 | pass |
| `/sso/initiate` → redirect_url with code | 200 | pass |
| `/sso/exchange` with valid code | claims returned | pass |
| Same code exchanged twice | 400 | pass |
| `/sso/exchange` with wrong secret | 401 | pass |
| `/sso/initiate` with non-allow-listed `redirect_uri` | 400 | pass |
| `/sso/exchange` with unknown code | 400 | pass |

## Not built (deliberately)

- **`/sso/provision`** — the doc's eager pre-fetch at login. It fires for every partner
  login including users who never open the trading app, and it drags in "keep the
  Surmount token TTL in lockstep with the partner session". Dropped as a premature
  optimization.
- **`GET /sso/start`** — the direct-arrival door for users who deep-link straight into
  blossom-fe. It requires the platform to maintain a session *cookie* alongside its JWT,
  because only a top-level browser navigation carries one. Add it if deep-linking becomes
  a real requirement.
