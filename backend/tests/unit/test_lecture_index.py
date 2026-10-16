"""Transcript ranking against objectives: tokens, BM25 with objective specificity, rules."""

from __future__ import annotations

from app.domain.lecture_index import Index, Query, objective_query, rank_lecture, specificity
from app.domain.lecture_rules import distinctive_domain_terms, domain_hints, rule_codes
from app.domain.lecture_text import document, tokenize


def test_tokenize_keeps_service_names_and_folds_plurals() -> None:
    assert tokenize("So, um, the S3 buckets and EC2 instances use Route-53 policies.") == [
        "s3",
        "bucket",
        "ec2",
        "instance",
        "route-53",
        "policy",
    ]
    assert tokenize("1 2 3 a I") == []


def _queries() -> list[Query]:
    iam = objective_query(
        "1.1",
        "1",
        "Design secure access to AWS resources",
        ["Federated access and identity services (IAM)", "Least privilege; the root user"],
        ["Who may do what: IAM, roles and least privilege"],
        ["A role is an identity with no long-term credentials; STS issues temporary ones."],
        ["Which policy grants least privilege to the batch job?"],
    )
    storage = objective_query(
        "3.1",
        "3",
        "Determine high-performing and scalable AWS storage solutions",
        ["AWS storage services with appropriate use cases (S3, EBS, EFS)"],
        ["Picking storage: S3, EBS and EFS"],
        ["S3 is object storage; EBS is a block device for one instance; EFS is shared files."],
        ["Which storage keeps the lowest cost for infrequent access?"],
    )
    return [iam, storage]


def test_a_lecture_ranks_under_the_objective_it_talks_about() -> None:
    queries = _queries()
    spec = specificity(queries)
    assert spec["aws"] < spec["iam"]  # "aws" sits in both queries and tells them apart less
    docs = [
        document(
            "a/iam.mp4",
            "In this lecture we look at IAM users, roles and policies. A role gives temporary "
            "credentials through STS, and least privilege means the policy grants only what the "
            "job needs. Never use the root user for daily work.",
        ),
        document(
            "a/s3.mp4",
            "S3 is object storage. For a block device attached to one EC2 instance you want EBS, "
            "and EFS is a shared file system. Storage classes trade cost for access frequency.",
        ),
        document("a/intro.mp4", "Welcome to the course. Let us begin with the exam itself."),
    ]
    index = Index(docs)
    iam_hits = rank_lecture(index, docs[0], queries, spec)
    assert iam_hits and iam_hits[0].code == "1.1" and iam_hits[0].normalized == 1.0
    assert "iam" in iam_hits[0].matched and "privilege" in iam_hits[0].matched
    storage_hits = rank_lecture(index, docs[1], queries, spec)
    assert storage_hits[0].code == "3.1"
    assert all(hit.code != "1.1" for hit in storage_hits)
    assert rank_lecture(index, docs[2], queries, spec) == []


def test_a_domain_hint_in_the_title_lifts_its_objectives() -> None:
    queries = _queries()
    spec = specificity(queries)
    doc = document("a/x.mp4", "Storage and access: S3 buckets with IAM policies and roles.")
    index = Index([doc, document("a/y.mp4", "Unrelated words about nothing in particular.")])
    plain = {hit.code: hit.score for hit in rank_lecture(index, doc, queries, spec)}
    lifted = {hit.code: hit.score for hit in rank_lecture(index, doc, queries, spec, {"3"})}
    assert lifted["3.1"] > plain["3.1"] and lifted.get("1.1", 0) <= plain.get("1.1", 0) + 1e-9


def test_rules_read_codes_from_titles_and_file_names() -> None:
    codes = ["1.1", "1.2", "2.1"]
    assert rule_codes(["1-cloud-design-principles-obj-1-1-and-1-2.md"], codes) == ["1.1", "1.2"]
    assert rule_codes(["2.1 Scaling patterns", "Objective 9.9 does not exist"], codes) == ["2.1"]
    assert rule_codes(["Kubernetes 1.35 release notes"], ["1.3"]) == []


def test_distinctive_domain_terms_ignore_shared_words() -> None:
    distinctive = distinctive_domain_terms(
        {
            "1": "Design Secure Architectures",
            "2": "Design Resilient Architectures",
            "4": "Design Cost-Optimized Architectures",
        }
    )
    assert distinctive["1"] == {"secure"} and distinctive["2"] == {"resilient"}
    assert "design" not in distinctive["4"] and "architecture" not in distinctive["4"]
    assert domain_hints(["Section 4: cost-optimized storage"], distinctive) == {"4"}
    assert domain_hints(["Designing architectures"], distinctive) == set()
