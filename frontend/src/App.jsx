import { Navigate, Route, Routes } from "react-router-dom";

import { AccountsProvider } from "./accounts";
import { RequireAuth } from "./auth";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import Developer from "./pages/Developer";
import Money from "./pages/Money";
import Profile from "./pages/Profile";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";

/** Signed-in routes share the shell; the auth screens deliberately don't —
 *  there is no account to navigate yet, so a rail would be furniture with
 *  nothing behind it. */
function Protected({ children }) {
  return (
    <RequireAuth>
      {/* Accounts load once, above the shell, so the topbar switcher and the
          page below it agree on which account is selected. */}
      <AccountsProvider>
        <AppShell>{children}</AppShell>
      </AccountsProvider>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignUp />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/money"
        element={
          <Protected>
            <Money />
          </Protected>
        }
      />
      <Route
        path="/profile"
        element={
          <Protected>
            <Profile />
          </Protected>
        }
      />
      <Route
        path="/developer"
        element={
          <Protected>
            <Developer />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
