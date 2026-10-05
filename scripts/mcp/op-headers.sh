#!/usr/bin/env sh
# Emit MCP connection headers as a JSON object on stdout (Claude Code `headersHelper`).
#
# CONTRACT: always exit 0, always print one JSON object.
# Printing `{}` means "no credential available" — Claude Code then sends no
# Authorization header, the remote server answers 401 + WWW-Authenticate, and
# Claude Code falls back to its own OAuth flow (`/mcp` or `claude mcp login`).
# Any non-JSON output or hard failure here would break the server instead of
# degrading it.
#
# TO ADD A SERVER: give it a `headersHelper` in .mcp.json pointing at this
# script, then add a `case` arm below mapping the server name to its 1Password
# secret reference. Servers with no arm get `{}` and stay keyless — that is a
# working state, not an error. Credential-free stdio servers (e.g.
# sequential-thinking) need no helper at all.
set -u

VAULT="${MCP_OP_VAULT:-agentic}"

say()       { printf '%s\n' "op-headers: $*" >&2; }   # one-line reason, stderr only
emit_none() { printf '{}\n'; exit 0; }

case "${CLAUDE_CODE_MCP_SERVER_NAME:-}" in
  github)   ref="op://${VAULT}/scm-github/token" ;;
  context7) ref="op://${VAULT}/svc-context7/password" ;;
  *)        say "no secret mapping for server '${CLAUDE_CODE_MCP_SERVER_NAME:-?}'; sending no auth header"
            emit_none ;;
esac

if ! command -v op >/dev/null 2>&1; then
  say "1Password CLI (op) not on PATH; '${CLAUDE_CODE_MCP_SERVER_NAME}' falls back to OAuth/keyless"
  emit_none
fi

# Claude Code does NOT pass settings.json `env` to a headersHelper, so the
# service-account token that reaches every other surface never reaches here.
# Without it `op` falls back to the 1Password desktop-app integration and
# raises an authorization dialog — one per HTTP server in .mcp.json, which is
# two back-to-back on every session open in a repo with github + context7.
# Read it instead from the login Keychain item chezmoi renders settings.json
# from: silent once `security` has been granted access, and a miss simply
# leaves the env as it was.
if [ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ] && command -v security >/dev/null 2>&1; then
  if kc=$(timeout 2 security find-generic-password -w \
            -s "${MCP_OP_KEYCHAIN_SERVICE:-claude-code-op-service-account}" \
            -a "${MCP_OP_KEYCHAIN_ACCOUNT:-$(id -un)}" 2>/dev/null) && [ -n "$kc" ]; then
    OP_SERVICE_ACCOUNT_TOKEN="$kc"
    export OP_SERVICE_ACCOUNT_TOKEN
  fi
  unset kc
fi

# 9s total budget (2 above + 7 here): Claude Code kills headersHelper at 10s.
if ! token=$(timeout 7 op read --no-newline "$ref" 2>/dev/null) || [ -z "$token" ]; then
  say "op could not resolve ${ref} (not signed in, no vault access, or offline); falling back to OAuth/keyless"
  emit_none
fi

printf '{"Authorization":"Bearer %s"}\n' "$token"
