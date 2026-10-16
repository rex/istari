"""Course names: which certification a downloaded course says it is for."""

from __future__ import annotations

from app.domain.naming import infer_exam, names_certification, names_other_level

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


def test_another_level_of_the_same_family_is_another_exam() -> None:
    assert names_other_level("AWS Certified Solutions Architect - Professional", SAA)
    assert names_other_level(
        "Udemy -Ultimate AWS Certified Solutions Architect Professional 2022", SAA
    )
    assert not names_other_level("Ultimate AWS Certified Solutions Architect Associate 2022", SAA)
    assert not names_other_level("AWS Certified Developer - Associate", SAA)
    assert not names_other_level("ZeroToMastery - AWS Solutions Architect", SAA)
    # A certification without a level word has no other level.
    assert not names_other_level(
        "Kubernetes Administrator Professional", "Certified Kubernetes Administrator"
    )


def test_infer_exam_reads_known_codes_only() -> None:
    assert infer_exam("Course 2021 [SAA-C02]").code == "SAA-C02"
    assert infer_exam("Identity Course 2024 [TST-C01]").code is None
