"""Model limits and batch planning for image-to-Mermaid conversion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelLimits:
    name: str
    rpm: int
    tpm: int
    rpd: int


# Limits are configuration defaults taken from Change_Requirements.md. They are
# intentionally isolated here because provider-side quotas can change.
DEFAULT_MODELS = (
    ModelLimits("gemini-3.1-flash-lite", rpm=15, tpm=250_000, rpd=500),
    ModelLimits("gemini-2.5-flash", rpm=5, tpm=250_000, rpd=20),
    ModelLimits("gemini-3.5-flash", rpm=5, tpm=250_000, rpd=20),
    ModelLimits("gemini-2.5-flash-lite", rpm=10, tpm=250_000, rpd=20),
    ModelLimits("gemini-3-flash", rpm=5, tpm=250_000, rpd=20),
)


@dataclass(frozen=True)
class PlannedDiagram:
    path: Path
    model: ModelLimits
    estimated_tokens: int


@dataclass(frozen=True)
class BatchPlan:
    assignments: tuple[PlannedDiagram, ...]
    unassigned: tuple[Path, ...]

    @property
    def estimated_seconds(self) -> float:
        by_model: dict[str, tuple[int, int]] = {}
        for item in self.assignments:
            count, rpm = by_model.get(item.model.name, (0, item.model.rpm))
            by_model[item.model.name] = (count + 1, rpm)
        return max((count / rpm * 60 for count, rpm in by_model.values()), default=0)


class BatchPlanner:
    def __init__(self, quota_ledger, models=DEFAULT_MODELS):
        self.ledger = quota_ledger
        self.models = tuple(models)

    def plan(
        self,
        files: list[Path],
        preferred_model: str | None = None,
        excluded_models: set[str] | None = None,
    ) -> BatchPlan:
        excluded_models = excluded_models or set()
        models = [model for model in self.models if model.name not in excluded_models]
        if preferred_model:
            models.sort(key=lambda model: model.name != preferred_model)

        capacity = {
            model.name: max(0, model.rpd - self.ledger.requests_today(model.name))
            for model in models
        }
        assignments: list[PlannedDiagram] = []
        unassigned: list[Path] = []
        model_index = 0

        for file_path in files:
            while model_index < len(models) and capacity[models[model_index].name] <= 0:
                model_index += 1
            if model_index >= len(models):
                unassigned.append(file_path)
                continue
            model = models[model_index]
            assignments.append(PlannedDiagram(file_path, model, estimate_image_tokens(file_path)))
            capacity[model.name] -= 1

        return BatchPlan(tuple(assignments), tuple(unassigned))


def estimate_image_tokens(path: Path) -> int:
    """Return a conservative planning estimate based on image dimensions."""
    try:
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
        tiles = max(1, ((width + 511) // 512) * ((height + 511) // 512))
        return 300 + tiles * 260
    except (ImportError, OSError):
        return 4_000
