import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import Avatar from "../components/Avatar";
import { INVESTMENTS_URL } from "../components/nav";
import { currency, shortDate, signedCurrency } from "../money";

const DISCOVERY_URL =
  (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9000") +
  "/.well-known/openid-configuration";

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.banking
      .summary()
      .then((data) => !cancelled && setSummary(data))
      .catch(() => {
        // The dashboard is still worth showing without balances — the hand-off,
        // which is the point of this app, does not depend on them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <header className="page-header greeting">
        <Avatar user={user} className="greeting-avatar" />
        <div>
          <h1>Welcome back, {user.first_name}</h1>
          <p>You are signed in to Blossom. Everything below is the partner side.</p>
        </div>
      </header>

      {summary && (
        <>
          <section className="balance-row">
            <div className="balance-card">
              <span className="balance-label">Total balance</span>
              <span className="balance-value">{currency(summary.total_balance)}</span>
              <span className="balance-meta">
                across {summary.accounts.length} account
                {summary.accounts.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="balance-card">
              <span className="balance-label">Money in · 30 days</span>
              <span className="balance-value is-in">
                {currency(summary.last_30_days.money_in)}
              </span>
            </div>
            <div className="balance-card">
              <span className="balance-label">Money out · 30 days</span>
              <span className="balance-value">
                {currency(summary.last_30_days.money_out)}
              </span>
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <div>
                <h2>Recent activity</h2>
              </div>
              <Link className="doc-link" to="/money">
                All transactions →
              </Link>
            </div>
            <ul className="txn-list">
              {summary.recent_transactions.map((t) => (
                <li className="txn" key={t.id}>
                  <span className={`txn-mark cat-${t.category}`} aria-hidden="true" />
                  <span className="txn-body">
                    <span className="txn-desc">{t.description}</span>
                    <span className="txn-meta">
                      {t.category_label} · {shortDate(t.posted_at)}
                      {t.status === "pending" && (
                        <span className="txn-pending"> · pending</span>
                      )}
                    </span>
                  </span>
                  <span
                    className={`txn-amount${Number(t.amount) > 0 ? " is-in" : ""}`}
                  >
                    {signedCurrency(t.amount)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      <section className="panel highlight">
        <h2>Investments</h2>
        <p>
          Opens the investing app. You will not be asked to sign in again — Blossom
          vouches for you in the background, and never shares your password.
        </p>
        {/* A plain anchor, deliberately. Blossom writes no JavaScript for this. */}
        <a className="btn" href={INVESTMENTS_URL}>
          Open Investments <span aria-hidden="true">→</span>
        </a>
      </section>

      <section className="panel">
        <h2>What that link does</h2>
        <p className="small">
          Here so the hand-off is visible while testing. A real platform shows none
          of this.
        </p>
        <dl>
          <dt>
            Your subject — OIDC <code>sub</code>
          </dt>
          <dd>
            <code>{user.external_user_id}</code>
            <span className="muted small">
              {" "}
              — immutable, never reused. Surmount matches on this and never on
              email, because emails get changed and recycled.
            </span>
          </dd>

          <dt>Your picture</dt>
          <dd>
            <code>{user.picture}</code>
            <span className="muted small">
              {" "}
              — assigned once at signup and never rewritten. Travels to Surmount as
              the OIDC <code>picture</code> claim.
            </span>
          </dd>

          <dt>Investments link</dt>
          <dd>
            <code>{INVESTMENTS_URL}</code>
            <span className="muted small">
              {" "}
              — no API call at click time. Surmount redirects you straight back to
              Blossom&rsquo;s <code>/oauth/authorize</code>, which sees your session
              cookie and answers with a code.
            </span>
          </dd>

          <dt>Discovery document</dt>
          <dd>
            <a href={DISCOVERY_URL} target="_blank" rel="noreferrer">
              /.well-known/openid-configuration
            </a>
            <span className="muted small">
              {" "}
              — the only URL Surmount was configured with. Every endpoint and
              signing key is read from here.
            </span>
          </dd>
        </dl>
      </section>
    </div>
  );
}
