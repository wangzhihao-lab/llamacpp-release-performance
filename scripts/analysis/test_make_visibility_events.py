"""Tests of make_visibility_events.py (no measurement; campaign values are faked).

Run: uv run --no-project --with pandas --with numpy --with pytest python3 -I -m pytest -q scripts/analysis/test_make_visibility_events.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_visibility_events as mv

MODELS = ("tinyllama-1.1b", "mistral-7b", "qwen2.5-1.5b")


def test_missing_series_covers_the_unmeasured_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mv.s2, "campaign_mean", lambda tag, m, b, t: 100.0 if tag == "b1" else 150.0)
    listed = [{"model": "mistral-7b", "backend": "cpu"}, {"model": "tinyllama-1.1b", "backend": "metal"}]
    row = {"tag_old": "b1", "tag_new": "b2", "series_json": json.dumps(listed)}
    out = mv.missing_series(row, MODELS)
    groups = {(s["model"], s["backend"]) for s in out}
    assert len(groups) == 4 and ("mistral-7b", "cpu") not in groups and ("tinyllama-1.1b", "metal") not in groups
    assert len(out) == 8 and {s["test"] for s in out} == {"pp512", "tg128"}
    assert all(abs(s["log_ratio"] - 0.4055) < 1e-3 and (s["tag_old"], s["tag_new"]) == ("b1", "b2") for s in out)


def test_confirmed_events_skip_v_and_duplicate_remeasures(tmp_path: Path) -> None:
    p = tmp_path / "judge_v11_events.csv"
    p.write_text("event_id,verdict_v11\nE01,C\nE01R,C\nE14,noise\nE14R,C\nVE01,C\nE02,A\n")
    assert mv.confirmed_events(p) == ["E01", "E14R"]
