# AWS labs on LocalEmu

A lab brief whose `verifier` names the `localemu` backend is an AWS task graded against
LocalEmu (image `localemu/localemu`, community edition 1.2.0), the AWS emulator the owner
runs in the lab. Unlike K16S, the tasks are Istari's own: each is a **scenario**, a small module
that sets the task up in the emulator with boto3, grades it by reading the state back, and
clears it away. The learner does the work with the AWS CLI in their own shell, pointed at
the emulator. Nothing here ever talks to real AWS, and Istari holds no AWS credentials.

Where the emulator runs, how it was built and how to repair it is the owner's runbook,
homelab-infrastructure-general `docs/localemu.md`. Its URL lives in the private inventory,
never in this repository.

## Configuration

| Variable | Purpose |
|---|---|
| `LOCALEMU_BASE_URL` | The emulator's gateway as the API process reaches it (`http://host:4566`, or its HTTPS ingress). Unset: AWS labs say which variable to set, exactly as K16S labs do. An `amazonaws.com` URL is refused at startup. |
| `LOCALEMU_REGION` | Default `us-east-1`. |
| `LOCALEMU_ACCESS_KEY_ID` | The identity Istari uses. Empty means the emulator's root (see below). |

The same URL is what the learner's shell uses: the lab's second step shows the `export`
lines (`AWS_ENDPOINT_URL`, the key id, a placeholder secret, the region), built by the
backend so the pack never names a host.

## What Istari asks of the emulator

- **Status:** `GET /_localemu/health`. It answers `{"edition", "version", "services", "uptime"}`.
  A background poll every 60 s keeps a snapshot, so `/api/health` (field `localemu`) and the
  planner never wait on it. A lab is scheduled only while the snapshot says reachable.
- **Everything else:** boto3, with `endpoint_url` set and both halves of the key pair passed
  explicitly, so the default credential chain is never consulted. Path-style S3 addressing,
  checksums only when an operation requires them, a 5 s connect and 30 s read timeout, and
  two attempts per call. Calls run off the event loop (`anyio.to_thread`).
- **Failures:** connection errors, timeouts and the emulator's refusals become an
  `UpstreamError` with a sentence an owner can act on (HTTP 502, nothing recorded). A bug in
  scenario code stays a bug.

## Emulator facts a scenario author needs

- **Identity is the access key id.** The emulator checks no signature, so any secret works.
- **Root is AWS's documentation example key id** (the one ending in `EXAMPLE`; the adapter
  holds it as `ROOT_ACCESS_KEY_ID`) and account `000000000000`. It is a published
  placeholder, not a credential. Unknown key ids get `403`
  "The security token included in the request is invalid".
- **IAM is enforced.** A user created in the emulator is denied until a policy allows it,
  and is allowed exactly what its policies name. `sts:GetCallerIdentity` and
  `s3:ListAllMyBuckets` pass for anyone.
- **State is ephemeral.** A restart is a clean slate, so a check must treat missing
  resources as ungradable, not as a fail (see below).
- **Engines are Docker-backed.** A NAT gateway takes about 4 s to show `available`. A
  Lambda function's runtime image is pulled on first use, so the first invoke is slow.

## Scenarios

A scenario lives in `backend/app/adapters/localemu/scenarios/<id>.py` (adapters, because it
does I/O) and is registered in that package's `REGISTRY`. It is a `Scenario`
(`adapters/localemu/scenario.py`):

| Field | What it is |
|---|---|
| `id` | The `question` a pack's verifier names, e.g. `s3-lifecycle`. Unique across families. |
| `profile` | The family a verifier names as its `profile`, e.g. `saa`. |
| `title`, `context`, `task`, `hint` | Istari's own text, shown live in the lab as plain paragraphs (not Markdown). |
| `setup(aws, ctx) -> str` | Makes the starting resources. Returns the output the learner reads, which names what it made. |
| `check(aws, ctx) -> CheckResult` | Reads the state back and grades it. |
| `solve(aws, ctx)` | Does the task by API, so tests and `make aws-labs-check` prove a solved run passes. |
| `teardown(aws, ctx)` | Removes every run of the scenario. |
| `weight` | Default 1. |

`aws` is an `Aws` helper with typed clients: `s3()`, `sts()`, `iam()`, `ec2()`, `sns()` and
`sqs()`. Add a method, and the matching `types-boto3` and `moto` extras, when a scenario
needs another service.

**Runs.** Every setup is a fresh run: `ctx.run` is six hex characters, stored on the
attempt row. Every resource a run makes starts with `ctx.prefix`
(`istari-<scenario>-<run>`). The client runs `teardown` before `setup`, and `teardown`
removes everything under `ctx.scenario_prefix` (`istari-<scenario>-`), so earlier attempts
never linger. A check grades the latest attempt's run, so a re-check after a fix grades the
same resources. v1 learners work as the emulator's root; a scoped learner user per attempt
would be one more field on `ScenarioContext`.

**Grading.** Use `scenarios/grading.py`: a header line, one `[ok]` or `[--]` line per clause,
then `PASS: …` or the first missed clause as `FAIL: …`. The last line is the reason shown
on the result card, as with a K16S grader.

**Ungradable is not a fail.** When the run's resources are gone (the learner deleted them,
or the emulator restarted), return `gone("…")`. It carries an `unavailable_reason`, the
lab says to set up again, and no attempt is recorded. A check with no setup behind it is
handled the same way by the client. The first graded attempt is evidence, so it must never
be an accident.

**Check what you can read.** Prefer reading configuration back over waiting for behaviour.
A lifecycle rule never runs while you watch. moto does not enforce IAM, so the
least-privilege check evaluates the policies itself (`scenarios/iam_eval.py`): explicit
Deny wins, IAM wildcards apply, and `Condition` statements are named rather than guessed.
SNS delivers to SQS whatever the queue policy says, so the policy is graded from its text
and the delivery separately.

## The labs

| Scenario | Lab brief | Lesson whose Do it shows it | Objective |
|---|---|---|---|
| `iam-least-privilege` | `lab-iam-least-privilege` | `lesson-iam-least-privilege` | 1.1 |
| `vpc-public-private` | `lab-vpc-public-private` | `lesson-network-and-data-security` | 1.2 |
| `sns-sqs-fanout` | `lab-sns-sqs-fanout` | `lesson-loose-coupling` | 2.1 |
| `s3-lifecycle` | `lab-s3-lifecycle` | `lesson-cost-optimized-storage` | 4.1 |
| `s3-versioning` | none yet | none | the adapter's own smoke scenario |

## Adding an AWS lab

1. Write the scenario module and register it. Keep every name under `ctx.prefix`.
2. Add the brief to the pack with
   `"verifier": {"backend": "localemu", "profile": "saa", "question": "<id>"}` and list it
   in its lesson's `labs`. A verified brief's `steps_md`, `cost_warning_md` and `cleanup_md`
   need only 20 characters, but say what the learner does, that it is free, and that the
   next setup clears it. The pack never names a host.
3. Tests: the parametrized loop in `tests/unit/test_localemu_scenarios.py` covers setup,
   fail, solve, pass and teardown for every registered scenario automatically. Add clause
   tests for the wrong answers your check must name (`tests/unit/test_localemu_aws_labs.py`).
4. `make aws-labs-check` against the emulator, then the gates.

## Developing without the emulator

The tests never need it. `tests/localemu_stub.py` serves the health endpoint through an
`httpx.MockTransport` (up, down, silent, unhealthy), and `moto_aws()` builds clients with no
endpoint for moto's in-process `mock_aws`, which intercepts only AWS's own endpoints.
LocalEmu is moto-derived, so behaviour mostly matches. Known gaps: moto does not enforce IAM
and loads none of AWS's managed policies, and S3 rejects a lifecycle filter that combines a
prefix and a tag outside `And`, as AWS does.

## Keeping the scenarios honest

`make aws-labs-check` (`labs aws-check`) runs every scenario against the configured emulator:
setup, check (must fail), solve, check (must pass), teardown. It also fails any pack lab whose
scenario this build lacks, and notes scenarios no lab uses yet. Exit 0, 1 (a scenario
misgraded or a lab names a missing scenario) or 2 (no emulator, or it did not answer). It is
not a gate, like `make labs-check`, because it needs the emulator. Pass `BASE_URL=` to point
it somewhere else, or `SCENARIO=` for one. It records nothing in Istari.
