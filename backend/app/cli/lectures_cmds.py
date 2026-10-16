"""`lectures eval`: the ranking against a hand-labelled sample, under a parameter set.

    uv run python -m app.cli lectures eval --sample ../corpus/eval/saa-c03.json --exam SAA-C03
    uv run python -m app.cli lectures eval --sample ... --floor 0.2 --generic-df 0.4

The sample is never committed (it names purchased lectures); `make lectures-eval` reads it
from the corpus. Each run prints the rates and every miss, so levers can be compared.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from app.adapters.db.engine import create_engine, dispose_engine
from app.adapters.db.models import ExamVersion
from app.adapters.db.session import session_factory
from app.config import settings
from app.domain.lecture_index import GENERIC_SHARE, MASS_POWER
from app.services.lecture_eval import Params, evaluate, load_sample


def cmd_eval(args: argparse.Namespace) -> int:
    path = Path(args.sample)
    if not path.is_file():
        print(f"error: no sample at {path}", file=sys.stderr)
        return 2
    sample = load_sample(path)
    params = Params(
        floor=args.floor,
        generic_share=args.generic_df,
        body_weight=args.body_weight,
        stem_weight=args.stem_weight,
        ceiling_quantile=args.ceiling_quantile,
        mass_power=args.mass_power,
        section_boost=args.section_boost,
        skip_housekeeping=args.housekeeping == "skip",
    )

    async def go() -> int:
        engine = create_engine(settings.database_url, pool_size=1, max_overflow=0)
        try:
            async with session_factory(engine)() as db:
                exam = await db.scalar(select(ExamVersion).where(ExamVersion.code == args.exam))
                if exam is None:
                    print(f"error: no exam version {args.exam}", file=sys.stderr)
                    return 2
                report = await evaluate(db, exam, sample, params)
        finally:
            await dispose_engine(engine)
        for line in report.lines():
            print(line)
        return 0

    return asyncio.run(go())


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    lectures = sub.add_parser("lectures", help="the lecture-to-objective index")
    lectures_sub = lectures.add_subparsers(dest="lectures_command", required=True)
    p = lectures_sub.add_parser("eval", help="rank a hand-labelled sample under a parameter set")
    p.add_argument(
        "--sample",
        required=True,
        help="JSON: {lectures: [{course_slug, lecture_path, objectives}]}",
    )
    p.add_argument("--exam", default="SAA-C03", help="the exam version code")
    p.add_argument(
        "--floor",
        type=float,
        default=0.0,
        help="drop a match below this share of its objective's best score",
    )
    p.add_argument(
        "--generic-df",
        type=float,
        default=GENERIC_SHARE,
        help="a term in more than this share of lectures is ignored",
    )
    p.add_argument(
        "--body-weight",
        type=float,
        default=1.0,
        help="weight of lesson bodies in the objective queries",
    )
    p.add_argument(
        "--stem-weight",
        type=float,
        default=1.0,
        help="weight of question stems in the objective queries",
    )
    p.add_argument(
        "--ceiling-quantile",
        type=float,
        default=1.0,
        help="the point of an objective's score distribution the floor is measured against",
    )
    p.add_argument(
        "--mass-power",
        type=float,
        default=MASS_POWER,
        help="divide a score by the query's mass to this power (0 none, 1 full)",
    )
    p.add_argument(
        "--section-boost",
        type=float,
        default=1.0,
        help="multiply a lecture's score for its section's top objectives (1 is off)",
    )
    p.add_argument(
        "--housekeeping",
        choices=("skip", "keep"),
        default="skip",
        help="skip (the build's behaviour) or keep welcome, course-tour and support lectures",
    )
    p.set_defaults(fn=cmd_eval)
