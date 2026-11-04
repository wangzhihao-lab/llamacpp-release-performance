"""List llama.cpp ``b<N>`` release tags with commit, commit date and distance.

Clones a blob-less, no-checkout copy of llama.cpp into ``repo/`` (or fetches
new tags if the clone already exists) and writes ``data/releases.csv`` with one
row per ``b<N>`` tag, sorted by build number:

    tag, build_number, commit, commit_date_utc, prev_tag, commits_since_prev

* ``commit`` is the full SHA the tag points to (annotated tags are peeled).
* ``commit_date_utc`` is the committer date of that commit in UTC (ISO 8601).
* ``commits_since_prev`` is ``git rev-list --count <prev_tag>..<tag>``, where
  ``prev_tag`` is the tag with the next-lower build number (empty for the
  first tag).

Only git is contacted (github.com over HTTPS); no API calls.

Run: python3 -I scripts/list_releases.py
"""

from __future__ import annotations

import argparse
import csv
import itertools
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/ggml-org/llama.cpp.git"
TAG_RE = re.compile(r"^b(\d+)$")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Release:
    """One ``b<N>`` release tag."""

    tag: str
    build_number: int
    commit: str
    commit_date_utc: str


def run_git(repo: Path, *args: str) -> str:
    """Run a git command inside ``repo`` and return its stdout.

    Args:
        repo: Path of the git repository.
        *args: Arguments passed to git after ``-C repo``.

    Returns:
        Standard output with trailing whitespace stripped.

    Raises:
        subprocess.CalledProcessError: If git exits with a non-zero status.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ensure_repo(repo: Path) -> None:
    """Clone llama.cpp without blobs or refresh its tags if already cloned.

    Args:
        repo: Destination directory of the clone.

    Raises:
        subprocess.CalledProcessError: If clone or fetch fails.
    """
    if (repo / "HEAD").exists() or (repo / ".git").exists():
        logger.info("fetching new tags into %s", repo)
        run_git(repo, "fetch", "--tags", "--prune", "--quiet", "origin")
        return
    logger.info("cloning %s into %s (blob:none, no checkout)", REPO_URL, repo)
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", REPO_URL, str(repo)],
        check=True,
    )


def to_utc(iso_date: str) -> str:
    """Convert an ISO 8601 date with offset to a UTC ``YYYY-MM-DDTHH:MM:SSZ`` string.

    Args:
        iso_date: Date as printed by ``git for-each-ref --format=%(committerdate:iso-strict)``.

    Returns:
        The same instant in UTC.
    """
    parsed = datetime.fromisoformat(iso_date)
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_releases(repo: Path) -> list[Release]:
    """Read all ``b<N>`` tags with their peeled commit and committer date.

    Args:
        repo: Path of the git repository.

    Returns:
        Releases sorted by build number.
    """
    fmt = "%(refname:strip=2)\t%(objectname)\t%(*objectname)\t%(committerdate:iso-strict)\t%(*committerdate:iso-strict)"
    out = run_git(repo, "for-each-ref", f"--format={fmt}", "refs/tags/b*")
    releases: list[Release] = []
    for line in out.splitlines():
        name, obj, peeled, date, peeled_date = (line.split("\t") + [""] * 5)[:5]
        match = TAG_RE.match(name)
        if not match:
            continue
        commit = peeled or obj
        commit_date = peeled_date or date
        if not commit_date:
            commit_date = run_git(repo, "show", "-s", "--format=%cI", commit)
        releases.append(Release(name, int(match.group(1)), commit, to_utc(commit_date)))
    releases.sort(key=lambda r: r.build_number)
    return releases


def count_between(repo: Path, prev: Release, cur: Release) -> int:
    """Count commits reachable from ``cur`` but not from ``prev``.

    Args:
        repo: Path of the git repository.
        prev: Earlier release.
        cur: Later release.

    Returns:
        Result of ``git rev-list --count prev..cur``.
    """
    return int(run_git(repo, "rev-list", "--count", f"{prev.commit}..{cur.commit}"))


def main() -> None:
    """Clone or refresh the repo and write ``data/releases.csv``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=ROOT / "repo")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "releases.csv")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ensure_repo(args.repo)
    releases = read_releases(args.repo)
    logger.info("found %d b-tags (%s .. %s)", len(releases), releases[0].tag, releases[-1].tag)

    pairs = list(itertools.pairwise(releases))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        counts = list(pool.map(lambda p: count_between(args.repo, p[0], p[1]), pairs))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["tag", "build_number", "commit", "commit_date_utc", "prev_tag", "commits_since_prev"])
        writer.writerow([releases[0].tag, releases[0].build_number, releases[0].commit, releases[0].commit_date_utc, "", ""])
        for (prev, cur), n in zip(pairs, counts):
            writer.writerow([cur.tag, cur.build_number, cur.commit, cur.commit_date_utc, prev.tag, n])
    tmp.replace(args.out)
    logger.info("wrote %s (%d rows)", args.out, len(releases))


if __name__ == "__main__":
    main()
