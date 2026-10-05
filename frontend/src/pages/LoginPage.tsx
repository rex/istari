import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { Brand } from "@/components/layout/Brand";
import { Button } from "@/components/ui/Button";
import { isApiError } from "@/lib/api";
import { useLogin } from "@/queries/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const error = login.error;
  let message: string | null = null;
  if (error) {
    if (isApiError(error, 429)) {
      const seconds = Number(error.details["retry_after_seconds"] ?? 0);
      message = `Too many attempts. Try again in about ${Math.ceil(seconds / 60)} minute(s).`;
    } else if (isApiError(error, 401)) message = "That username and password did not match.";
    else message = "Could not reach Istari. Check the server and try again.";
  }

  return (
    <main className="login">
      <div className="card login__card stack">
        <Brand large />
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            login.mutate({ username, password }, { onSuccess: () => void navigate({ to: "/" }) });
          }}
        >
          <label className="field">
            <span className="field__label">Username</span>
            <input
              className="input"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span className="field__label">Password</span>
            <input
              className="input"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {message ? (
            <p role="alert" className="save-status save-status--error">
              {message}
            </p>
          ) : null}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="btn--block"
            busy={login.isPending}
          >
            Enter
          </Button>
          <p className="muted small" style={{ margin: 0 }}>
            Single-owner login. No registration. Create the owner with{" "}
            <code>make bootstrap-owner</code>.
          </p>
        </form>
      </div>
    </main>
  );
}
