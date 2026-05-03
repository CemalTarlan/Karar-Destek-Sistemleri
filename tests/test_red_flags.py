"""Red-flag detector tests."""

from __future__ import annotations

from pathlib import Path

from medsim.rules.red_flags import RedFlagDetector


def test_red_flags_load(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    assert len(detector.patterns) >= 5
    ids = {p.id for p in detector.patterns}
    assert "RF-CARDIAC-01" in ids


def test_red_flags_no_match_on_innocuous_text(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    hits = detector.scan("Hafif bir baş ağrım var, dün geceden beri.")
    assert hits == []


def test_red_flags_cardiac_combination(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    text = "Göğsümde sıkışma var, ağrı sol koluma yayılıyor."
    hits = detector.scan(text)
    ids = {h.id for h in hits}
    assert "RF-CARDIAC-01" in ids


def test_red_flags_neuro_combination(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    text = "Aniden konuşma bozukluğum oldu, yüzümün bir tarafı düşmüş gibi."
    hits = detector.scan(text)
    ids = {h.id for h in hits}
    assert "RF-NEURO-01" in ids


def test_red_flags_partial_does_not_fire(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    # Only one of the AND-groups present.
    text = "Göğsümde hafif bir his var."
    ids = {h.id for h in detector.scan(text)}
    assert "RF-CARDIAC-01" not in ids


def test_red_flags_ascii_folding(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    # User typed without Turkish diacritics — must still fire.
    text = "Gogusumde sikisma var, agri sol koluma yayiliyor."
    hits = detector.scan(text)
    ids = {h.id for h in hits}
    assert "RF-CARDIAC-01" in ids


def test_red_flags_empty_text(red_flags_path: Path) -> None:
    detector = RedFlagDetector(patterns_path=red_flags_path)
    assert detector.scan("") == []
