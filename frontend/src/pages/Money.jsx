import { useEffect, useState } from "react";

import { useAccounts } from "../accounts";
import { api } from "../api";
import { currency, fullDate, shortDate, signedCurrency } from "../money";

function TransactionRow({ transaction }) {
  const outgoing = Number(transaction.amount) < 0;
  return (
    <li className="txn">
      <span className={`txn-mark cat-${transaction.category}`} aria-hidden="true" />
      <span className="txn-body">
        <span className="txn-desc">{transaction.description}</span>
        <span className="txn-meta">
          {transaction.category_label} · {shortDate(transaction.posted_at)}
          {transaction.status === "pending" && (
            <span className="txn-pending"> · pending</span>
          )}
        </span>
      </span>
      <span className={`txn-amount${outgoing ? "" : " is-in"}`}>
        {signedCurrency(transaction.amount)}
      </span>
    </li>
  );
}

export default function Money() {
  const { accounts, selected, selectedId, setSelectedId, error } = useAccounts();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    setDetail(null);

    api.banking
      .transactions(selectedId)
      .then((data) => !cancelled && setDetail(data))
      .catch((err) => !cancelled && setLoadError(err.message));

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  if (error || loadError) {
    return (
      <div className="page">
        <p className="error" role="alert">
          {error ?? loadError}
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Money</h1>
        <p>Your accounts and everything that has moved through them.</p>
      </header>

      <div className="account-cards">
        {(accounts ?? []).map((account) => (
          <button
            key={account.id}
            type="button"
            className={`account-card${account.id === selectedId ? " is-active" : ""}`}
            onClick={() => setSelectedId(account.id)}
          >
            <span className="account-card-kind">{account.kind_label}</span>
            <span className="account-card-name">{account.name}</span>
            <span className="account-card-balance">
              {currency(account.balance, account.currency)}
            </span>
            <span className="account-card-meta">
              {account.display_number}
              {account.available_balance !== account.balance && (
                <>
                  {" "}
                  · {currency(account.available_balance, account.currency)} available
                </>
              )}
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <section className="panel">
          <div className="section-head">
            <div>
              <h2>{selected.name}</h2>
              <p className="small">
                {selected.display_number} · opened {fullDate(selected.opened_at)}
              </p>
            </div>
            <span className="account-card-balance">
              {currency(selected.balance, selected.currency)}
            </span>
          </div>

          {!detail ? (
            <p className="muted small">Loading transactions…</p>
          ) : detail.transactions.length === 0 ? (
            <p className="muted small">Nothing has moved through this account yet.</p>
          ) : (
            <ul className="txn-list">
              {detail.transactions.map((transaction) => (
                <TransactionRow key={transaction.id} transaction={transaction} />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
