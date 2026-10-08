# The private corpus

Istari can read purchased course material (video courses with subtitle tracks, cheat
sheets, study-guide PDFs and EPUBs, Udemy quiz and practice-test exports) and turn it
into two private things: a text corpus and drill packs. Both live outside git.

| What | Where | Committed? |
|---|---|---|
| Converted text (transcripts, cheat sheets, books) | `corpus/<course-slug>/` | never (gitignored) |
| Drill packs built from quiz/practice-test exports | `content/private/<slug>.json` | never (gitignored) |
| The tooling and its tests | `backend/app/corpus/`, `backend/app/cli/corpus_cmds.py` | yes |

The repository is public. Nothing derived from purchased material is committed, and the
tests use synthetic samples shaped like the exports, never the exports themselves.

## What the corpus is for, and what it is not

- **Coverage maps.** A course's section list and transcripts show what an instructor
  thought the exam expects. Comparing that against a pack's objectives finds gaps.
- **Drafting input.** The draft pipeline (rex/istari#15) can read a transcript to learn
  *which* scenarios matter for an objective. The facts in a drafted item still come from
  current AWS documentation with checked dates, never from the transcript.
- **Drill material.** Imported quiz questions are a way to practise recall. They are
  `draft`, authored by the vendor, not source-checked, and they live in their own
  `<EXAM>-DRILL` exam version so they never mix with a verified pack's objectives.
- **Not a fact source.** Course material is dated (see the table below) and unverified.
  An item whose only source is a course is a `draft` and stays one.

## Commands

```bash
# One course directory -> corpus/<course-slug>/ with a manifest.json
make corpus-ingest SRC="/Volumes/MinasTirith-Data/MinasTirith-Learning/Cloud/AWS/AWS Certified Solutions Architect Associate Training SAA-C03"

# A whole topic folder: every child directory (and loose PDF/EPUB) is a course
make corpus-ingest SRC="/Volumes/MinasTirith-Data/MinasTirith-Learning/Kubernetes/CKA" ALL=1

# Udemy quiz HTML files and/or practice-test results PDFs -> one private pack per exam
make corpus-udemy INPUTS="'/path/08 S3/095 [quiz] S3 Quiz.html' '/path/Practice Test #1.pdf'" \
  EXAM=SOA-C02 SLUG=udemy-sysops-2021 NAME="SysOps 2021 course quizzes"

# Validate and import the private pack like any other (dry run first)
cd backend && uv run python -m app.cli validate-pack ../content/private/udemy-sysops-2021.json
cd backend && uv run python -m app.cli import-pack ../content/private/udemy-sysops-2021.json --dry-run
```

Conversion uses local tools found on `PATH`: subtitle tracks (SRT, WebVTT) are handled
natively; HTML, EPUB and DOCX go through `pandoc`; PDFs through `pdftotext` (poppler).
Ingestion never writes to the source directory, skips tracker junk and link-only
"lesson web page" files, and drops a VTT when the same lecture already has an SRT.

### Quiz and results exports

- A Udemy **section quiz** saved as HTML (the accordion export with "Question N",
  numbered badges, "Correct Answer" and "Explanation") parses fully, multi-answer
  questions included. The quiz name becomes the drill pack's domain, so Progress can
  still say which topic is weak.
- A Udemy **practice-test results** PDF (the "Results" page printed to PDF) parses stem,
  options, the `(Correct)` markers, the per-option rationales under "Incorrect options"
  and the AWS documentation links under "References", which become the item's sources.
- Questions the parser cannot make valid (no correct answer, duplicate options, fewer
  than two distractors, more than six options) are reported and left out rather than
  imported broken. True/false questions always fall out: the schema needs two
  distractors.

First run on 2026-10-07: the six DVA-C01 practice tests parsed to 368 of 389 questions
(12 without a detectable marker, 7 over-segmented by code blocks, 2 duplicates); the
SysOps 2021 quizzes to 185 of 198 and the Cloud Practitioner 2021 quizzes to 172 of
187 (the rest true/false). All three packs validate and import in dry run. The Digital
Cloud SAA-C03 course ingested to 312 transcript and cheat-sheet files, 236k words, in
18 seconds over SMB.

## What the AWS library holds (checked 2026-10-07)

Counts under `MinasTirith-Learning/Cloud/AWS`: 20,123 files; 6,935 videos with 4,960 VTT
and 4,487 SRT tracks; 656 HTML; 239 PDF; 25 EPUB. Only two courses ship quiz HTML (40
quizzes). Six practice-test PDFs exist, all DVA-C01.

| Material | Made for | Current exam | Use |
|---|---|---|---|
| Digital Cloud SAA-C03 training (SRT, exam crams, cheat-sheet links) | SAA-C03 | SAA-C03 | coverage map, drafting input |
| Udemy Ultimate SAA-C03 (Maarek), SAA-C02 2021, "The Ultimate SAA" | SAA-C03 / C02 | SAA-C03 | coverage map; C02 content for fundamentals only |
| Udemy DOP-C02 2023 | DOP-C02 | DOP-C02 | coverage map when that track exists |
| Udemy DVA-C02 training; DVA-C01 practice tests (6 PDFs) | DVA-C02 / C01 | DVA-C02 | drill pack (C01, dated); coverage map |
| Udemy SysOps 2021 + 21 quizzes; SOA-C02 2022 course | SOA-C02 | SOA-C03 (CloudOps, since 2025-09-30) | drill pack for fundamentals; containers and multi-account scope is missing |
| Udemy Security Specialty 2022; SCS-C01 course | SCS-C01 | SCS-C02 | fundamentals only |
| Cloud Practitioner 2021 + 19 quizzes; CLF-C02 course | CLF-C01 / C02 | CLF-C02 | drill pack; low priority |
| ANS-C01 course (CBT Nuggets 2022) and study guide 2e 2023 | ANS-C01 | ANS-C01 | coverage map |
| Sybex SAA-C03 Study Guide 4e (2023), Pearson Cert Guide 2e | SAA-C03 | SAA-C03 | chapter review questions as private drill; reference reading |
| A Cloud Guru 2020 courses, 2018 zips, SAA-C01/SOA-C01 practice-test books | retired versions | n/a | fundamentals only; skip for exam prep |

Kubernetes courses (`MinasTirith-Learning/Kubernetes`) have almost no subtitle tracks
(CKA 3 of 476 videos, CKAD 0 of 394). Local transcription with Whisper is feasible on
this machine but is a separate, slow job; the filenames of the "100 CKA practice
questions" course already read as a task checklist for rex/istari#10.
