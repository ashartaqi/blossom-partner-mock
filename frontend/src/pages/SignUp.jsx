import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import AuthLayout from "../components/AuthLayout";
import FloatingInput from "../components/FloatingInput";

export default function SignUp() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signUp(form);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <AuthLayout
        title="Create your account"
        description="This is the partner platform, not the investing app."
        footer={
          <>
            <button type="submit" className="btn btn-block" disabled={busy}>
              {busy ? "Creating…" : "Create account"}
            </button>
            <p className="auth-alt">
              Already have one? <Link to="/signin">Sign in</Link>
            </p>
          </>
        }
      >
        <div className="auth-fields">
          <div className="row">
            <FloatingInput
              label="First name"
              value={form.first_name}
              onChange={update("first_name")}
              autoComplete="given-name"
              required
              autoFocus
            />
            <FloatingInput
              label="Last name"
              value={form.last_name}
              onChange={update("last_name")}
              autoComplete="family-name"
              required
            />
          </div>
          <FloatingInput
            label="Email"
            type="email"
            value={form.email}
            onChange={update("email")}
            autoComplete="email"
            required
          />
          <FloatingInput
            label="Password"
            type="password"
            value={form.password}
            onChange={update("password")}
            autoComplete="new-password"
            minLength={8}
            hint="At least 8 characters."
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
