import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api } from "./api";

const AccountsContext = createContext(null);

/** The member's accounts, fetched once and shared.
 *
 *  Held above both the topbar switcher and the Money page so the two agree on
 *  which account is selected — and so switching in the header does not need a
 *  second round-trip on the page that reads it. */
export function AccountsProvider({ children }) {
  const [accounts, setAccounts] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const rows = await api.banking.accounts();
      setAccounts(rows);
      setSelectedId((current) => {
        if (current && rows.some((a) => a.id === current)) return current;
        return (rows.find((a) => a.is_primary) ?? rows[0])?.id ?? null;
      });
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selected = accounts?.find((a) => a.id === selectedId) ?? null;

  return (
    <AccountsContext.Provider
      value={{ accounts, selected, selectedId, setSelectedId, error, reload: load }}
    >
      {children}
    </AccountsContext.Provider>
  );
}

export function useAccounts() {
  const context = useContext(AccountsContext);
  if (!context) throw new Error("useAccounts must be used inside <AccountsProvider>");
  return context;
}
