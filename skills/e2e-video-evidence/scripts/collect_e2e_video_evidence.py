#!/usr/bin/env python3
"""Run an E2E command and preserve videos, traces, screenshots, reports, and logs."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Iterable


EVIDENCE_EXTENSIONS = {
    ".webm",
    ".mp4",
    ".mov",
    ".mkv",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".json",
    ".html",
    ".xml",
}

VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".mkv"}

COMMON_E2E_PARTS = (
    "test-results",
    "playwright-report",
    "playwright/.cache",
    "cypress/videos",
    "cypress/screenshots",
    "cypress/reports",
    "allure-results",
    "allure-report",
    "e2e-results",
    "e2e-artifacts",
    "coverage",
)

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".nuxt",
    "dist",
    "build",
    ".turbo",
    ".cache",
    "__pycache__",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an E2E command and collect generated video evidence."
    )
    parser.add_argument(
        "--output-dir",
        default="e2e-evidence",
        help="Root directory for evidence bundles. Default: e2e-evidence",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Readable run name for the evidence folder.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Extra glob pattern to collect. Repeatable.",
    )
    parser.add_argument(
        "--max-file-mb",
        type=int,
        default=500,
        help="Skip artifacts larger than this size. Default: 500",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Do not copy artifacts; only write logs and manifest.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("provide a command after --")
    return args


def slugify(value: str, fallback: str = "e2e-run") -> str:
    result = []
    for char in value.lower():
        if char.isalnum():
            result.append(char)
        elif char in ("-", "_", ".", " "):
            result.append("-")
    slug = "".join(result).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:80] or fallback


def should_skip_dir(path: Path, evidence_root: Path) -> bool:
    if path == evidence_root or evidence_root in path.parents:
        return True
    return path.name in SKIP_DIRS


def is_common_e2e_path(path: Path) -> bool:
    normalized = path.as_posix()
    return any(part in normalized for part in COMMON_E2E_PARTS)


def matches_extra_include(path: Path, patterns: Iterable[str]) -> bool:
    text = path.as_posix()
    return any(fnmatch.fnmatch(text, pattern) for pattern in patterns)


def iter_candidate_files(
    root: Path,
    evidence_root: Path,
    start_time: float,
    include_patterns: list[str],
    max_bytes: int,
) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not should_skip_dir(current_path / dirname, evidence_root)
        ]
        for filename in filenames:
            path = current_path / filename
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size > max_bytes:
                continue

            suffix = path.suffix.lower()
            rel = path.relative_to(root)
            modified_during_run = stat.st_mtime >= start_time - 1
            known_artifact = suffix in EVIDENCE_EXTENSIONS and is_common_e2e_path(rel)
            included = matches_extra_include(rel, include_patterns)

            if included or (suffix in EVIDENCE_EXTENSIONS and modified_during_run) or known_artifact:
                candidates.append(path)
    return sorted(set(candidates))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_artifacts(files: list[Path], root: Path, artifacts_dir: Path) -> list[dict]:
    records = []
    for source in files:
        rel = source.relative_to(root)
        destination = artifacts_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        stat = source.stat()
        records.append(
            {
                "source": str(source),
                "stored_as": str(destination),
                "relative_path": rel.as_posix(),
                "bytes": stat.st_size,
                "sha256": sha256_file(destination),
                "kind": "video" if source.suffix.lower() in VIDEO_EXTENSIONS else "artifact",
            }
        )
    return records


def write_summary(bundle_dir: Path, manifest: dict) -> None:
    videos = [item for item in manifest["artifacts"] if item["kind"] == "video"]
    lines = [
        "# E2E Evidence Summary",
        "",
        f"- Status: {'passed' if manifest['exit_code'] == 0 else 'failed'}",
        f"- Exit code: {manifest['exit_code']}",
        f"- Command: `{' '.join(manifest['command'])}`",
        f"- Started: {manifest['started_at']}",
        f"- Finished: {manifest['finished_at']}",
        f"- Duration seconds: {manifest['duration_seconds']:.2f}",
        f"- Artifact count: {len(manifest['artifacts'])}",
        f"- Video count: {len(videos)}",
        "",
    ]
    if videos:
        lines.append("## Videos")
        lines.append("")
        for video in videos:
            lines.append(f"- `{video['relative_path']}` ({video['bytes']} bytes)")
    else:
        lines.extend(
            [
                "## Videos",
                "",
                "- No video files were found. Confirm that the E2E framework has video recording enabled.",
            ]
        )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `run.log`")
    lines.append("- `manifest.json`")
    lines.append("- `DISPLAY.md`")
    lines.append("- `artifacts/`")
    lines.append("")
    (bundle_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def display_path(record: dict) -> str:
    stored_as = record.get("stored_as")
    return stored_as or record["source"]


def write_display(bundle_dir: Path, manifest: dict) -> None:
    videos = [item for item in manifest["artifacts"] if item["kind"] == "video"]
    lines = [
        "# E2E Evidence Display",
        "",
        "Paste the Markdown below into the final response so the user sees the video inline.",
        "",
    ]
    if videos:
        for index, video in enumerate(videos, start=1):
            path = display_path(video)
            lines.append(f"## Video {index}: {video['relative_path']}")
            lines.append("")
            lines.append(f"![E2E evidence video {index}]({path})")
            lines.append("")
    else:
        lines.append("No video files were found to display inline.")
        lines.append("")
    (bundle_dir / "DISPLAY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    evidence_root = (root / args.output_dir).resolve()
    timestamp = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    run_name = slugify(args.name or " ".join(args.command[:3]))
    bundle_dir = evidence_root / f"{timestamp}-{run_name}"
    artifacts_dir = bundle_dir / "artifacts"
    bundle_dir.mkdir(parents=True, exist_ok=False)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    started_at = dt.datetime.now(dt.timezone.utc).astimezone()
    start_time = time.time()
    log_path = bundle_dir / "run.log"

    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"$ {' '.join(args.command)}\n\n")
        log.flush()
        process = subprocess.Popen(
            args.command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        exit_code = process.wait()

    finished_at = dt.datetime.now(dt.timezone.utc).astimezone()
    max_bytes = args.max_file_mb * 1024 * 1024
    candidates = iter_candidate_files(
        root=root,
        evidence_root=evidence_root,
        start_time=start_time,
        include_patterns=args.include,
        max_bytes=max_bytes,
    )
    if args.no_copy:
        artifact_records = [
            {
                "source": str(path),
                "stored_as": None,
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "kind": "video" if path.suffix.lower() in VIDEO_EXTENSIONS else "artifact",
            }
            for path in candidates
        ]
    else:
        artifact_records = copy_artifacts(candidates, root, artifacts_dir)

    manifest = {
        "command": args.command,
        "cwd": str(root),
        "evidence_dir": str(bundle_dir),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "exit_code": exit_code,
        "artifacts": artifact_records,
        "log": str(log_path),
    }
    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_summary(bundle_dir, manifest)
    write_display(bundle_dir, manifest)

    video_count = sum(1 for item in artifact_records if item["kind"] == "video")
    print(f"\nEvidence directory: {bundle_dir}")
    print(f"Artifacts collected: {len(artifact_records)}")
    print(f"Videos collected: {video_count}")
    print(f"Inline display snippet: {bundle_dir / 'DISPLAY.md'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
