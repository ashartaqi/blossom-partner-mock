import { useEffect, useRef, useState } from "react";

import { useAccounts } from "../accounts";
import { currency } from "../money";
import { IconChevronDown } from "./icons";

/** The header's account pill. Real accounts, real balances, switchable.
 *
 *  It used to be a hardcoded name and a made-up last-four that never changed. */
export default function AccountSwitcher() {
  const { accounts, selected, setSelectedId } = useAccounts();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close on an outside click or Escape — a menu that only closes by picking
  // something traps anyone who opened it by accident.
  useEffect(() => {
    if (!open) return undefined;

    const onPointerDown = (event) => {
      if (!ref.current?.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!selected) {
    return <span className="account-pill is-empty">No accounts</span>;
  }

  return (
    <div className="switcher" ref={ref}>
      <button
        type="button"
        className="account-pill"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className={`account-dot kind-${selected.kind}`} aria-hidden="true" />
        <span className="account-text">
          <span className="account-name">{selected.name}</span>
          <span className="account-number">
            {selected.display_number} · {currency(selected.balance, selected.currency)}
          </span>
        </span>
        <IconChevronDown className="account-chevron" />
      </button>

      {open && (
        <ul className="switcher-menu" role="listbox">
          {accounts.map((account) => (
            <li key={account.id}>
              <button
                type="button"
                role="option"
                aria-selected={account.id === selected.id}
                className={`switcher-item${account.id === selected.id ? " is-active" : ""}`}
                onClick={() => {
                  setSelectedId(account.id);
                  setOpen(false);
                }}
              >
                <span className={`account-dot kind-${account.kind}`} aria-hidden="true" />
                <span className="account-text">
                  <span className="account-name">{account.name}</span>
                  <span className="account-number">{account.display_number}</span>
                </span>
                <span className="switcher-balance">
                  {currency(account.balance, account.currency)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
