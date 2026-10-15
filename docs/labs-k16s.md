# Verified labs on K16S

A lab brief with a `verifier` is graded by a backend the owner runs. The first backend is
[K16S](https://github.com/immanuwell/k16s-exam-simulator): a real kubeadm cluster with two
workers, a browser terminal and a small exam server whose questions each carry a setup
script (puts the cluster into the task's starting state) and a validate script (inspects the
cluster and exits 0 on pass, printing one reason line). Istari never installs or provisions
K16S; it talks to a running instance and records the verdicts as evidence.

## Licence

K16S is PolyForm Noncommercial 1.0.0. Personal use is permitted; redistribution of its
question text is not ours to do, and this repository is public. **No K16S text (titles,
descriptions, hints, scripts) is ever committed here.** A pack references question ids
only; the lab page fetches the text live from the instance and shows it with attribution.

## Configuration

| Variable | Purpose |
|---|---|
| `K16S_BASE_URL` | The exam server as the API process reaches it (`http://host:8080`). Unset: verified labs explain that no backend is configured, exactly as Watch does without `LEARNING_ROOT`. |
| `K16S_PUBLIC_URL` | What the browser opens for the terminal and the exam UI. Defaults to the base URL. Needed when the API pod and the browser reach the instance by different paths. |
| `HEADLAMP_URL` | Optional link to a cluster map, opened in a new tab. |

The terminal (`/terminal/`) is plain HTTP on the LAN and Istari is served over HTTPS, so the
lab page opens it in a new tab rather than embedding it (an iframe would be blocked as mixed
content). The exam server has no authentication: keep the instance on the LAN or a tailnet.

## The API contract (verified against the repository, HEAD 08f0ba1)

| Method | Path | Body / result |
|---|---|---|
| GET | `/api/status` | `{ok, session, profiles[], mode}`; `mode` is `lightweight` under kind |
| GET | `/api/session` | current session or 404 |
| POST | `/api/session/start` | `{"profile":"cka","duration_secs":7200}`; ends any running session |
| POST | `/api/session/end` | |
| GET | `/api/questions?profile=cka` | `{questions:[{id,title,weight,context,description,hint,requires}]}` |
| POST | `/api/questions/{id}/setup` | `{ok, output}`; or `{unavailable:true, reason}`; 60 s limit |
| POST | `/api/questions/{id}/check` | `{passed, output}`; or `{unavailable:true, reason}`; 30 s limit |

Profiles are the instance's `exams/<profile>/` directories (`cka`, `cka2`, `cks`, …); question
ids are the YAML file names. A question with `requires: heavy` cannot run under the
lightweight (kind) install; the server answers `unavailable` with a reason, which Istari
shows as the reason, not as an error.

## Session policy

K16S allows one active session, and starting one ends the previous. Istari starts a session
lazily on the first setup, reuses it while it is active and on the same profile, and switches
profile only when a lab needs it. Client timeouts: setup 90 s, check 45 s, reads 10 s.

## Status without waiting

The client keeps a status snapshot, refreshed every 60 s in the background. `/api/health`
reports `k16s: {configured, reachable, mode, profiles, checked_at}` from that snapshot and
never calls the instance itself; the planner reads the same snapshot to decide whether a
verified lab can be scheduled. The question list per profile is cached for 60 s.

## Errors

A transport failure, a timeout or a non-2xx answer becomes `upstream_error` (HTTP 502) with a
plain sentence such as "K16S at http://… did not answer within 45 s". No attempt is recorded
on a transport failure. Retries are the owner's click, never automatic.

## Istari's own API

| Method | Path | Result |
|---|---|---|
| GET | `/api/labs/{key}/verifier` | configured/reachable state, the instance's mode and active profile, terminal and map links, the live task text, an `unavailable_reason` when the task cannot run in the current mode, a one-sentence `message` when something is in the way, the attempt history |
| POST | `/api/labs/{key}/setup` | ensures a session on the lab's profile, runs the setup script, records an attempt (`setup_at`) |
| POST | `/api/labs/{key}/check` | ensures the session, runs the validate script, grades the open attempt (or a fresh one when nothing was set up) with `passed`, the output and the duration |

An `unavailable` answer records nothing and is returned as the reason. A transport failure
is `upstream_error` (502) and records nothing. The grader's output is capped at 16 KB; its
last line is the reason shown on the lab card ("last checked 3 min ago, failed: …").

## Adding a verified lab

```json
{
  "slug": "cka-fix-crashloop",
  "objectives": ["5.2"],
  "title": "Fix a pod that keeps crashing",
  "estimated_minutes": 10,
  "goals_md": "...", "prerequisites_md": "...", "cost_warning_md": "Runs on the lab cluster; costs nothing.",
  "steps_md": "Set up, work in the terminal, check.", "expected_observations_md": "...", "cleanup_md": "The next setup resets the environment.",
  "verifier": {"backend": "k16s", "profile": "cka", "question": "02-fix-crashloop", "weight": 5}
}
```

Write the brief fields in your own words; the task text comes from the instance. Map the
objectives by hand to the track's domains. `make labs-check` compares every verified lab's
question id with what the configured instance serves and lists questions no lab covers.

## Developing without an instance

`tests/k16s_stub.py` is a small FastAPI app serving the seven endpoints with canned data
(its own placeholder text, pass/fail per question id, an injectable delay). The integration
and Playwright suites run against it:

```bash
cd backend && uv run uvicorn tests.k16s_stub:app --port 8081
K16S_BASE_URL=http://127.0.0.1:8081 make dev
```
