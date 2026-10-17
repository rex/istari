"""A LocalEmu scenario: Istari's own task text, and how to set it up, grade it and clear it.

Unlike K16S tasks, the text is ours, so it lives with the scenario. A scenario is plain
functions over `Aws` clients and a `ScenarioContext`; the client runs them off the event loop
and turns botocore's failures into owner sentences, so a scenario only handles the errors that
are part of grading (a missing bucket is a FAIL, not an outage).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.adapters.localemu.aws import Aws
from app.domain.verifier import CheckResult, VerifierQuestion


@dataclass(frozen=True, slots=True)
class ScenarioContext:
    """One attempt's names: every resource a run makes starts with `prefix`.

    `run` is the attempt's id, kept on its attempt row so the check grades what that setup
    made. Teardown clears everything under `scenario_prefix`, every run of the scenario, so a
    fresh setup leaves nothing from earlier attempts behind. v1 learners work as the
    emulator's root; a scoped learner user per attempt would be one more field here.
    """

    scenario: str
    run: str
    region: str

    @property
    def scenario_prefix(self) -> str:
        return f"istari-{self.scenario}-"

    @property
    def prefix(self) -> str:
        return f"{self.scenario_prefix}{self.run}"


SetupFn = Callable[[Aws, ScenarioContext], str]
CheckFn = Callable[[Aws, ScenarioContext], CheckResult]
TeardownFn = Callable[[Aws, ScenarioContext], None]
SolveFn = Callable[[Aws, ScenarioContext], None]


@dataclass(frozen=True, slots=True)
class Scenario:
    """`setup` returns the output shown to the learner (it names what it made); `check`
    returns the verdict, its last line `PASS: …` or `FAIL: …` like a K16S grader's; `solve`
    does the task by API, so `make aws-labs-check` and the tests prove a solved run passes.
    A check that cannot grade (the run's resources are gone) returns `unavailable_reason`."""

    id: str
    # The scenario family a pack's verifier names as its `profile` (`saa`).
    profile: str
    title: str
    # What setup leaves behind, the task, and the hint: plain text, shown live in the lab.
    context: str
    task: str
    setup: SetupFn
    check: CheckFn
    teardown: TeardownFn
    solve: SolveFn
    hint: str = ""
    weight: int = 1

    def question(self) -> VerifierQuestion:
        return VerifierQuestion(
            id=self.id,
            title=self.title,
            weight=self.weight,
            context=self.context,
            description=self.task,
            hint=self.hint,
        )


class ScenarioRegistry:
    """Every scenario by id. Ids are unique across families, like K16S question ids."""

    def __init__(self, scenarios: Iterable[Scenario]) -> None:
        self._by_id: dict[str, Scenario] = {}
        for scenario in scenarios:
            if scenario.id in self._by_id:
                raise ValueError(f"two LocalEmu scenarios share the id '{scenario.id}'")
            self._by_id[scenario.id] = scenario

    @property
    def profiles(self) -> tuple[str, ...]:
        return tuple(sorted({s.profile for s in self._by_id.values()}))

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))

    def get(self, scenario_id: str) -> Scenario | None:
        return self._by_id.get(scenario_id)

    def for_profile(self, profile: str) -> list[Scenario]:
        return sorted((s for s in self._by_id.values() if s.profile == profile), key=lambda s: s.id)
