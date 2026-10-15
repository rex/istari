"""The shipped CKA pack: the v1.35 track with one verified lab per K16S question, by id only."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import parse_pack, validate_pack

PACK_PATH = Path(__file__).resolve().parents[3] / "content" / "packs" / "k8s-cka-k16s" / "pack.json"


def _load() -> ContentPackSpec:
    return parse_pack(json.loads(PACK_PATH.read_text(encoding="utf-8")))


def test_pack_validates_and_covers_both_mocks() -> None:
    spec = _load()
    report = validate_pack(spec)
    assert report.ok, report.as_dict()
    counts = (len(spec.lessons), len(spec.questions), len(spec.flashcards), len(spec.labs))
    assert counts == (0, 0, 0, 36)
    by_profile = Counter(lab.verifier.profile for lab in spec.labs if lab.verifier)
    assert by_profile == {"cka": 18, "cka2": 18}
    assert sum(domain.weight_percent for domain in spec.domains) == 100
    assert [domain.code for domain in spec.domains] == ["1", "2", "3", "4", "5"]


def test_every_lab_references_one_k16s_question() -> None:
    spec = _load()
    objectives = {o.code for d in spec.domains for o in d.objectives}
    seen: set[tuple[str, str]] = set()
    for lab in spec.labs:
        verifier = lab.verifier
        assert verifier is not None and verifier.backend == "k16s"
        assert lab.slug == f"{verifier.profile}-{verifier.question}"
        assert (verifier.profile, verifier.question) not in seen
        seen.add((verifier.profile, verifier.question))
        assert set(lab.objectives) <= objectives, lab.slug
        # Two minutes per weight point is the pack's convention for the estimate.
        assert lab.estimated_minutes == 2 * verifier.weight
    covered = {code for lab in spec.labs for code in lab.objectives}
    assert covered >= {"1.1", "1.4", "2.2", "2.5", "3.2", "3.3", "4.3", "5.1", "5.2", "5.4"}


def test_heavy_tasks_are_tagged_for_the_full_install() -> None:
    spec = _load()
    heavy = sorted(lab.slug for lab in spec.labs if "needs-full-install" in lab.tags)
    assert heavy == ["cka-01-fix-notready-node", "cka-10-static-pod"]


def test_exam_facts_say_what_is_estimated() -> None:
    exam = _load().exam_version
    assert exam.duration_minutes == 120 and exam.passing_scaled_score == 66
    assert exam.verification.status == "verified" and exam.verification.checked_on is not None
    assert "estimate" in exam.verification.notes
