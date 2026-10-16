"""Course names: which certification a downloaded course says it is for."""

from __future__ import annotations

from app.domain.naming import infer_exam, names_certification

SAA = "AWS Certified Solutions Architect - Associate"


def test_names_certification_wants_every_distinctive_word() -> None:
    assert names_certification("Ultimate AWS Certified Solutions Architect Associate 2022", SAA)
    assert names_certification("AWS Certified Solutions Architect - Associate 2018", SAA)
    # The Professional course and a course that never says "Associate" are not this exam.
    assert not names_certification("AWS Certified Solutions Architect - Professional", SAA)
    assert not names_certification("ZeroToMastery - AWS Solutions Architect - Zero to Mastery", SAA)
    # Vendor and "certified" carry no information: a name made of them matches nothing.
    assert not names_certification("AWS Certified Everything", "AWS Certified")
    assert names_certification(
        "Certified Kubernetes Administrator (CKA) with Practice Tests",
        "Certified Kubernetes Administrator",
    )


def test_infer_exam_reads_known_codes_only() -> None:
    assert infer_exam("Course 2021 [SAA-C02]").code == "SAA-C02"
    assert infer_exam("Identity Course 2024 [TST-C01]").code is None
