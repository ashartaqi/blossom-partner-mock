import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import AuthLayout from "../components/AuthLayout";
import FloatingInput from "../components/FloatingInput";

export default function SignIn() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(form);
      // Back where they were headed before RequireAuth intercepted them.
      navigate(location.state?.from ?? "/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <AuthLayout
        title="Welcome back"
        description="Sign in to continue."
        footer={
          <>
            <button type="submit" className="btn btn-block" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
            <p className="auth-alt">
              No account? <Link to="/signup">Create one</Link>
            </p>
          </>
        }
      >
        <div className="auth-fields">
          <FloatingInput
            label="Email"
            type="email"
            value={form.email}
            onChange={update("email")}
            autoComplete="email"
            required
            autoFocus
          />
          <FloatingInput
            label="Password"
            type="password"
            value={form.password}
            onChange={update("password")}
            autoComplete="current-password"
            required
          />
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </div>
      </AuthLayout>
    </form>
  );
}
