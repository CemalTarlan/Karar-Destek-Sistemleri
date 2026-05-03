"""Evaluation metrics — skeleton.

Bodies are intentionally TODO. Faz 3'te eval setiyle birlikte doldurulacak.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from medsim.schemas.triage import TriageColor


class ConfusionMatrix(TypedDict):
    """3x3 confusion matrix indexed by (true_color, predicted_color)."""

    matrix: dict[TriageColor, dict[TriageColor, int]]
    total: int


def compute_confusion_matrix(
    predictions: Sequence[TriageColor],
    labels: Sequence[TriageColor],
) -> ConfusionMatrix:
    """Build a confusion matrix from parallel sequences.

    # TODO: Faz 3 — gerçek implementasyon. Aşağıdaki iskelet tipleri
    # kullanılarak doldurulacak; ayrıca renk-ağırlıklı F1, accuracy ve
    # macro-recall hesapları eklenecek.
    """
    raise NotImplementedError("Faz 3'te eval setiyle birlikte doldurulacak.")


def compute_false_negative_rate(
    predictions: Sequence[TriageColor],
    labels: Sequence[TriageColor],
    critical_color: TriageColor = TriageColor.KIRMIZI,
) -> float:
    """Fraction of cases where the true label is `critical_color` but the
    prediction is *not*. The headline safety metric — target = 0.0.

    # TODO: Faz 3 — gerçek implementasyon.
    """
    raise NotImplementedError("Faz 3'te eval setiyle birlikte doldurulacak.")
