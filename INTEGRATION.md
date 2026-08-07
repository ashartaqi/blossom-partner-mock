# What Surmount needs from Blossom

Everything on this page is standard OpenID Connect. If Blossom already runs an
identity provider — for staff SSO, for a mobile app, for anything — most of this
is already done and the work is registering one more client.

---

## The short version

**You give us three values. We give you one URL. You add a link.**

| You give us | Example |
|---|---|
| Issuer URL | `https://id.blossom.com` |
| Client ID | `surmount-investing` |
| Client secret | sent over 1Password / your secrets manager, never email or Slack |

| We give you | Example |
|---|---|
| Redirect URI to allow-list | `https://api.surmount.ai/api/sso/blossom/callback/` |
| The link for your sidebar | `https://api.surmount.ai/api/sso/blossom/start/` |

That is the integration. There is no SDK to install and no API for your frontend
to call.

---

## 1. Your provider

We read everything else from your discovery document, so these URLs are yours to
choose and yours to change:

```
GET https://id.blossom.com/.well-known/openid-configuration
```

It needs to advertise, and support:

| | Value | Why |
|---|---|---|
| `response_types_supported` | includes `code` | Authorization Code flow. The token never touches the browser. |
| `grant_types_supported` | includes `authorization_code` | |
| `code_challenge_methods_supported` | includes `S256` | PKCE. We always send it; please require it. |
| `id_token_signing_alg_values_supported` | `RS256` or better | Asymmetric. You keep the private key; we only ever hold the public one. |
| `jwks_uri` | reachable, public | Where we fetch the key to verify signatures. Cache-friendly, please. |
| `scopes_supported` | `openid`, `profile`, `email` | |

We do **not** need: implicit flow, hybrid flow, refresh tokens, dynamic client
registration, or client-initiated backchannel auth.

---

## 2. The claims we read

From the ID token, or from `/userinfo` if you keep the token minimal:

| Claim | Required | What we do with it |
|---|---|---|
| `sub` | **yes** | The permanent link between your member and their Surmount account |
| `email` | **yes** | Creating the account; matching an existing one |
| `email_verified` | strongly preferred | If `true`, we skip our own verification email |
| `given_name`, `family_name` | preferred | Their name in the app, and a KYC prefill |
| `picture` | optional | Their avatar. Must be an `https` URL. |

### `sub` is the one that matters

Two properties, and the whole design rests on both:

- **It never changes** for a given person.
- **It is never reused** for a different one.

We store it and match on it forever. We deliberately do *not* match on email —
emails get changed and recycled, and matching a recycled email would hand one
person another person's brokerage account.

A UUID primary key gives you both properties for free. An email address, a
username, or a sequential ID that gets reissued after deletion gives you neither.

### `email_verified` is load-bearing

If you send `true`, we take your word for it and skip our own verification mail.
If your platform lets someone set an email address without proving they own it,
send `false` — otherwise that becomes a way to take over a Surmount account.

---

## 3. Allow-list our redirect URI

```
https://api.surmount.ai/api/sso/blossom/callback/
```

**Exact match, no wildcards, no prefix matching.** Loose redirect-URI matching is
the most reliably exploited bug in OAuth deployments: anything looser lets an
attacker append their own host and receive the authorization code.

Also worth registering, so sign-out returns members to you:

```
https://app.blossom.com/dashboard          (post_logout_redirect_uri)
```

---

## 4. Add the link

```html
<a href="https://api.surmount.ai/api/sso/blossom/start/">Investments</a>
```

A plain anchor. Not `fetch`, not `XMLHttpRequest`, not a popup.

The hand-off is a chain of redirects that has to carry cookies across origins —
your session cookie on the way to `/authorize`, ours on the way back. Only a
top-level navigation does that. An XHR would be blocked cross-origin, could not
follow the chain, and could not hold the cookies.

**Nothing happens at click time.** Your frontend makes no API call, mints nothing,
and holds nothing. If a member never taps Investments, no request is ever made.

Optional: `?next=/portfolio` sends them to a specific page once signed in. We
accept it only as a path on our own app, never an absolute URL.

---

## 5. Marking us trusted

Surmount is first-party — Blossom handing a Blossom member to Blossom's own
investing product. Register the client so it **skips the consent screen**.
Otherwise every member is asked whether Blossom may share their name with
Blossom, which is noise that teaches people to click through consent prompts.

---

## What we handle

You do not need to build, and should not build:

- account creation on our side — first arrival creates it, silently
- linking a member who already has a Surmount account — we adopt it
- a signup form, a password, or an email confirmation
- phone verification — our KYC flow collects and OTP-verifies it later
- retries, expiry, and error screens

---

## What happens on our side, for your security review

1. `/start/` generates `state`, `nonce` and a PKCE verifier, stores them
   server-side, and puts only a random handle in an `HttpOnly`, `SameSite=Lax`
   cookie.
2. Your `/authorize` redirects the browser back with `code` and `state`.
3. We compare `state` in constant time against the stored value, **before any
   network call**. A mismatch stops everything — that is the login-CSRF defence.
4. Back-channel `POST` to your token endpoint with the code, our client secret in
   an `Authorization: Basic` header, and the PKCE verifier.
5. We verify the ID token against your JWKS: signature, `iss`, `aud`, `exp`,
   `iat`, `nonce`, and an algorithm allow-list that refuses `none` and `HS256`.
6. The flow record is deleted on use, so a callback URL sitting in history is
   worth nothing.
7. Our own JWT is never put in a URL. The redirect to the whitelabel carries a
   single-use handle with a 60-second life, traded for tokens over a POST.

Every decision — minted, verified, adopted, created, refused and why — is written
to an audit log.

---

## If you have no OpenID Provider

Then the honest question is whether standing one up is worth it, and usually it
is: your framework almost certainly has a library.

| Stack | Library |
|---|---|
| Python | `authlib` |
| Node | `node-oidc-provider` |
| Java / Spring | Spring Authorization Server |
| .NET | Duende IdentityServer, OpenIddict |
| Go | `fosite` |
| Ruby | `doorkeeper` + OIDC extension |

`backend/oidc/` in this repository is the `authlib` version, working, with tests.

If it genuinely is not on the table, we support a simpler two-endpoint fallback —
see `backend/sso/`. It is weaker in ways worth knowing before choosing it: the
secret is symmetric so both sides can mint what the other verifies, nothing is
signed so there is no artefact to re-verify later, and the flow can only start on
your side. Ask us and we will send the spec.
