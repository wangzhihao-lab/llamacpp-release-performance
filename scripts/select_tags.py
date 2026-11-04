"""Select time-equidistant llama.cpp releases for the benchmark campaign.

Reads ``data/releases.csv`` (from list_releases.py) and builds a time grid of
``n`` points between ``start`` (default 2023-09-01T00:00:00Z) and the commit
date of the newest tag:

    t_i = start + i * (end - start) / n,   i = 0 .. n-1

For each grid point the chosen release is the first tag whose commit date is
at or after ``t_i`` (ties broken by the lower build number); if that tag was
already chosen, the next unused tag is taken. The newest tag is appended, so
the default campaign has 80 + 1 = 81 tags.

Writes ``data/selected_tags.txt`` (one tag per line, chronological, the input
of run_campaign.sh) and ``data/selected_tags.csv`` (grid point, tag, commit,
commit date, build number).

Run: python3 -I scripts/select_tags.py [--n 80] [--start 2023-09-01]
"""

from __future__ import annotations

import argparse
import bisect
import csv
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Row:
    """One release row from ``releases.csv``."""

    tag: str
    build_number: int
    commit: str
    date: datetime


def parse_utc(text: str) -> datetime:
    """Parse ``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SSZ`` into an aware UTC datetime.

    Args:
        text: Date string.

    Returns:
        Timezone-aware datetime in UTC.
    """
    if len(text) == 10:
        return datetime.fromisoformat(text).replace(tzinfo=UTC)
    return datetime.fromisoformat(text).astimezone(UTC)  # Python >= 3.11 parses a trailing Z


def load_releases(path: Path) -> list[Row]:
    """Load releases sorted by (commit date, build number).

    Args:
        path: Path of ``releases.csv``.

    Returns:
        Sorted release rows.
    """
    with path.open(newline="") as fh:
        rows = [
            Row(r["tag"], int(r["build_number"]), r["commit"], parse_utc(r["commit_date_utc"]))
            for r in csv.DictReader(fh)
        ]
    rows.sort(key=lambda r: (r.date, r.build_number))
    return rows


def select(rows: list[Row], start: datetime, n: int) -> list[tuple[datetime | None, Row]]:
    """Pick one release per grid point plus the newest release.

    Args:
        rows: Releases sorted by (date, build number).
        start: First grid point.
        n: Number of grid points.

    Returns:
        List of (grid point, release); the appended newest release has grid point ``None``
        unless it was already picked.

    Raises:
        ValueError: If no release exists at or after ``start``.
    """
    newest = max(rows, key=lambda r: r.build_number)
    end = newest.date
    if end <= start:
        raise ValueError("newest release is older than the start date")
    dates = [r.date for r in rows]
    step = (end - start) / n
    chosen: list[tuple[datetime | None, Row]] = []
    used: set[str] = set()
    for i in range(n):
        target = start + i * step
        k = bisect.bisect_left(dates, target)
        while k < len(rows) and rows[k].tag in used:
            k += 1
        if k >= len(rows):
            logger.warning("no unused release at or after %s", target.isoformat())
            continue
        chosen.append((target, rows[k]))
        used.add(rows[k].tag)
    if newest.tag not in used:
        chosen.append((None, newest))
    return chosen


def main() -> None:
    """Write ``selected_tags.txt`` and ``selected_tags.csv``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--releases", type=Path, default=ROOT / "data" / "releases.csv")
    parser.add_argument("--start", default="2023-09-01")
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "selected_tags.txt")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    rows = load_releases(args.releases)
    chosen = select(rows, parse_utc(args.start), args.n)
    chosen.sort(key=lambda item: (item[1].date, item[1].build_number))

    args.out.write_text("".join(f"{row.tag}\n" for _, row in chosen))
    with args.out.with_suffix(".csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["idx", "grid_point_utc", "tag", "build_number", "commit", "commit_date_utc"])
        for idx, (target, row) in enumerate(chosen):
            grid = target.strftime("%Y-%m-%dT%H:%M:%SZ") if target else "newest"
            writer.writerow([idx, grid, row.tag, row.build_number, row.commit, row.date.strftime("%Y-%m-%dT%H:%M:%SZ")])
    logger.info("selected %d tags: %s .. %s", len(chosen), chosen[0][1].tag, chosen[-1][1].tag)


if __name__ == "__main__":
    main()
