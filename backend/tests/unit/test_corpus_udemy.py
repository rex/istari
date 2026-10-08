"""Udemy exports (quiz HTML, results PDF text) parse into questions that make a valid pack."""

from __future__ import annotations

from datetime import date

from app.corpus.private_pack import ParsedQuestion, PrivatePackMeta, build_private_pack
from app.corpus.udemy_quiz import parse_quiz_html
from app.corpus.udemy_results import parse_results_text
from app.domain.content.validate import parse_pack, validate_pack

# The exporter's accordion template, reduced to the pieces the parser keys on.
QUIZ_HTML = """
<div class="panel-heading"><h4 class="panel-title">
<a role="button" href="#question1">Question 1</a></h4></div>
<div id="question1"><div class="panel-body">
<div class="panel-heading"><h4 class="panel-title">
<p>Which class is cheapest for archives with no retrieval requirement?</p></h4></div>
<div class="radio"><span class="badge">1</span>
<label><input type="radio"><p>Amazon Glacier</p></label></div>
<div class="radio"><span class="badge">2</span>
<label><input type="radio"><p>Glacier Deep Archive</p></label></div>
<div class="radio"><span class="badge">3</span>
<label><input type="radio"><p>S3 Standard-IA</p></label></div>
<div class="radio"><span class="badge">4</span>
<label><input type="radio"><p>S3 Intelligent-Tiering</p></label></div>
<h4 class="panel-title"><a href="#answer1">Correct Answer</a></h4>
<div id="answer1" class="panel-collapse collapse"><div class="panel-body">
<div><span class="badge">2</span> <div><p>Glacier Deep Archive</p></div></div>
<div class="alert" role="alert"><h4><strong>Explanation</strong></h4>
<div class="alert" role="alert">
<p>Deep Archive is the cheapest &amp; retrieval takes hours.</p><p>Second paragraph.</p>
</div></div>
</div></div></div></div>
<div class="panel-heading"><h4 class="panel-title">
<a role="button" href="#question2">Question 2</a></h4></div>
<div id="question2"><div class="panel-body">
<div class="panel-heading"><h4 class="panel-title">
<p>Which TWO are regional services?</p></h4></div>
<div class="radio"><span class="badge">1</span>
<label><input type="checkbox"><p>IAM</p></label></div>
<div class="radio"><span class="badge">2</span>
<label><input type="checkbox"><p>Amazon VPC</p></label></div>
<div class="radio"><span class="badge">3</span>
<label><input type="checkbox"><p>Amazon EC2</p></label></div>
<div class="radio"><span class="badge">4</span>
<label><input type="checkbox"><p>Route 53</p></label></div>
<div class="radio"><span class="badge">5</span>
<label><input type="checkbox"><p>CloudFront</p></label></div>
<h4 class="panel-title"><a href="#answer2">Correct Answer</a></h4>
<div id="answer2" class="panel-collapse collapse"><div class="panel-body">
<div><span class="badge">2</span> <div><p>Amazon VPC</p></div></div>
<div><span class="badge">3</span> <div><p>Amazon EC2</p></div></div>
<div class="alert" role="alert"><h4><strong>Explanation</strong></h4>
<div class="alert" role="alert"><p>VPC and EC2 are regional.</p></div></div>
</div></div></div></div>
</body></html>
"""

# pdftotext output of a results page: paragraphs separated by blank lines, "(Correct)"
# on its own line after the option it marks, a form feed at a page break.
RESULTS_TEXT = """Practice Test #1 (AWS Certified Developer Associate -
DVA-C01) - Results
Question 1: Correct
You are a developer working on Lambda functions behind API Gateway. The team lead
asked you to format the data response.
Which feature of API Gateway can be used?
Use a Lambda custom interceptor

Use an API Gateway stage variable

Deploy an interceptor shell script

Use API Gateway Mapping Templates

(Correct)

Explanation
Correct option:
Use API Gateway Mapping Templates - API Gateway lets you use mapping templates to map
the payload from a method request to the integration request.
Incorrect options:
Deploy an interceptor shell script - This option has been added as a distractor.
Use an API Gateway stage variable - Stage variables are name-value pairs; not useful here.
Use a Lambda custom interceptor - This is a made-up option.
References:
https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-data-
transformations.html

Question 2: Incorrect
Which TWO statements about KMS are true? (Select two)
KMS stores the CMK and encrypts data sent
by clients

(Correct)

KMS generates a new CMK for each Encrypt call

KMS keys never leave the service unencrypted

(Correct)

KMS sends the CMK to the client

Explanation
Correct options:
KMS stores the CMK and encrypts data sent by clients - The CMK never leaves KMS.
\fKMS keys never leave the service unencrypted - Key material stays inside KMS.
Incorrect options:
KMS generates a new CMK for each Encrypt call - Data keys are generated, not CMKs.
KMS sends the CMK to the client - Never.
References:
https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html
Question 3: Skipped
"""

META = PrivatePackMeta(
    slug="udemy-test",
    name="Test drill",
    vendor="Test vendor",
    exam_code="DVA-C01",
    exam_name="Developer Associate (DVA-C01)",
    certification_slug="aws-certified-developer-associate",
    certification_name="AWS Certified Developer - Associate",
    authored_on=date(2026, 10, 7),
    source_title="Test vendor: Test drill",
)


def test_quiz_html_parses_single_and_multi_answer_questions() -> None:
    questions = parse_quiz_html(QUIZ_HTML, group="S3")
    assert [q.stem for q in questions] == [
        "Which class is cheapest for archives with no retrieval requirement?",
        "Which TWO are regional services?",
    ]
    first, second = questions
    assert first.options[1] == "Glacier Deep Archive" and first.correct == [1]
    assert (
        first.explanation
        == "Deep Archive is the cheapest & retrieval takes hours.\n\nSecond paragraph."
    )
    assert second.correct == [1, 2] and len(second.options) == 5
    assert first.group == "S3"


def test_results_text_parses_options_markers_rationales_and_references() -> None:
    questions = parse_results_text(RESULTS_TEXT, group="Practice Test #1")
    assert len(questions) == 2, "the skipped question has no body and is dropped"
    first, second = questions
    assert first.stem.endswith("Which feature of API Gateway can be used?")
    assert first.options == [
        "Use a Lambda custom interceptor",
        "Use an API Gateway stage variable",
        "Deploy an interceptor shell script",
        "Use API Gateway Mapping Templates",
    ]
    assert first.correct == [3]
    assert first.rationales[2].startswith("This option has been added as a distractor")
    assert first.rationales[0] == "This is a made-up option."
    assert first.references == [
        "https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-data-transformations.html"
    ]
    assert second.correct == [0, 2]
    assert second.options[0] == "KMS stores the CMK and encrypts data sent by clients"
    assert second.explanation.startswith("Correct options:")
    assert second.rationales == {
        1: "Data keys are generated, not CMKs.",
        3: "Never.",
    }


def test_parsed_questions_build_a_pack_the_validator_accepts() -> None:
    questions = parse_quiz_html(QUIZ_HTML, group="S3") + parse_results_text(
        RESULTS_TEXT, group="Practice Test #1"
    )
    questions.append(ParsedQuestion(stem="Broken: no answer", options=["a", "b", "c"], correct=[]))
    questions.append(ParsedQuestion(stem="Dup", options=["a", "a", "b"], correct=[0]))
    pack, rejected = build_private_pack(questions, META)
    assert [reason for _, reason in rejected] == [
        "no usable correct answer",
        "duplicate option texts",
    ]

    spec = parse_pack(pack)
    report = validate_pack(spec)
    assert report.ok, report.errors
    assert spec.exam_version.code == "DVA-C01-DRILL"
    assert [d.name for d in spec.domains] == ["S3", "Practice Test #1"]
    assert all(
        q.review_status == "draft" and not q.provenance.source_checked for q in spec.questions
    )
    multi = next(q for q in spec.questions if q.stem_md.startswith("Which TWO are regional"))
    assert multi.select_count == 2 and sorted(multi.correct_option_ids) == ["o2", "o3"]
    assert set(multi.distractor_rationales) == {"o1", "o4", "o5"}
    kms = next(q for q in spec.questions if "KMS" in q.stem_md)
    assert kms.sources[0].url.endswith("concepts.html")
