# Session context
mode: greenfield
stack: python-fastapi + react-vite (SPA)
cloud: none (local Postgres via compose; no AWS resources or credentials)
visibility: public-oss (github.com/rex/istari)
autonomy: continue-until-blocked
created: 2026-10-05T16:00:00-05:00
updated: 2026-10-05T17:30:00-05:00
fast_path: false

## Q5 freeform notes
- Built from Pierce's implementation brief `istari-agent-kickstart.md` (his copy; not
  committed). Brand assets in `brand/`.
- Work is tracked in Rivendell: rex/istari#1 (V1 parent), #2 slice 1, #3 slice 2,
  #4 slice 3, #5 deployment notes.
- Hard limits from the brief: no homelab changes, no public deploy, no cloud commands,
  no AWS provisioning. Secrets are actively scanned (pre-commit, CI, GitHub).
- Content is AI-authored and `source_checked` against AWS docs on 2026-10-05; human
  review is the next step (TASK_STATE.md §5).
