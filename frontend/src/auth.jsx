import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { api, endSession, tokens } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On boot, a token in storage is only a claim. Ask the backend who it belongs to
  // before treating anyone as logged in.
  useEffect(() => {
    if (!tokens.access) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => {
        tokens.clear();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = {
    user,
    loading,
    async signIn(credentials) {
      const data = await api.login(credentials);
      tokens.set(data);
      setUser(data.user);
      return data.user;
    },
    async signUp(payload) {
      const data = await api.signup(payload);
      tokens.set(data);
      setUser(data.user);
      return data.user;
    },
    signOut() {
      tokens.clear();
      // The bearer token and the server session are two separate credentials.
      // Dropping only the token would leave the session cookie alive, and the
      // next hand-off would sign the member straight back in — looking, from
      // their side, like sign-out did nothing.
      endSession();
      setUser(null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

export function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="centered muted">Checking your session…</div>;
  if (!user) return <Navigate to="/signin" state={{ from: location.pathname }} replace />;
  return children;
}
