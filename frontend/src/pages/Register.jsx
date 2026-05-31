import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { formatApiError } from "../utils/apiError.js";
import { PASSWORD_HINT, validatePassword } from "../utils/passwordRules.js";

export default function Register() {
  const { register, loading } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    const passwordCheck = validatePassword(password);
    if (!passwordCheck.ok) {
      setError(passwordCheck.message);
      return;
    }
    try {
      await register(email, fullName, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(formatApiError(err, "Registration failed"));
    }
  }

  return (
    <div className="auth-card">
      <h1>Create your account</h1>
      <p className="muted">Start placing orders in minutes.</p>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Full name
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            minLength={1}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
          <span className="muted small">{PASSWORD_HINT}</span>
        </label>
        {error && <div className="alert error">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>
      <p className="muted center">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}
