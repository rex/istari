"""The persisted scheduler configuration rows and the scheduler built from them."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import SchedulerConfig
from app.domain.scheduling.fsrs_adapter import DEFAULT_SETTINGS, FsrsScheduler, library_version
from app.domain.scheduling.interface import SchedulerSettings


def settings_from_config(config: SchedulerConfig) -> SchedulerSettings:
    return SchedulerSettings(
        name=config.name,
        parameters=tuple(float(p) for p in config.parameters),
        desired_retention=config.desired_retention,
        learning_steps_seconds=tuple(int(s) for s in config.learning_steps_seconds),
        relearning_steps_seconds=tuple(int(s) for s in config.relearning_steps_seconds),
        maximum_interval=config.maximum_interval,
        enable_fuzzing=config.enable_fuzzing,
    )


def build_scheduler(config: SchedulerConfig) -> FsrsScheduler:
    return FsrsScheduler(settings_from_config(config))


async def get_default_config(db: AsyncSession) -> SchedulerConfig:
    config = await db.scalar(
        select(SchedulerConfig).where(SchedulerConfig.name == DEFAULT_SETTINGS.name)
    )
    if config is None:
        config = SchedulerConfig(
            name=DEFAULT_SETTINGS.name,
            library="py-fsrs",
            library_version=library_version(),
            parameters=list(DEFAULT_SETTINGS.parameters),
            desired_retention=DEFAULT_SETTINGS.desired_retention,
            learning_steps_seconds=list(DEFAULT_SETTINGS.learning_steps_seconds),
            relearning_steps_seconds=list(DEFAULT_SETTINGS.relearning_steps_seconds),
            maximum_interval=DEFAULT_SETTINGS.maximum_interval,
            enable_fuzzing=DEFAULT_SETTINGS.enable_fuzzing,
        )
        db.add(config)
        await db.flush()
    return config
