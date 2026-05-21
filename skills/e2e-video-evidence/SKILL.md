---
name: e2e-video-evidence
description: Capture and preserve evidence for E2E test runs, especially browser test videos. Use when Codex is asked to run E2E tests, verify UI flows with video proof, leave evidence of an executed video test, collect Playwright/Cypress recordings, or produce a timestamped bundle containing test logs, videos, traces, screenshots, reports, and a manifest.
---

# E2E Video Evidence

Use this skill whenever an E2E run should leave auditable evidence. The expected output is a timestamped evidence directory containing the command log, manifest, generated videos, traces, screenshots, reports, and a concise summary for the user.

## Quick Start

Prefer the bundled collector when the E2E command is known:

```bash
python3 /path/to/e2e-video-evidence/scripts/collect_e2e_video_evidence.py -- npm run test:e2e
```

The collector:

- Runs the command from the current project directory.
- Saves stdout/stderr to `e2e-evidence/<timestamp>-<command>/run.log`.
- Copies new or modified evidence files into `artifacts/`.
- Writes `manifest.json` and `SUMMARY.md`.
- Exits with the wrapped command's exit code.

If the command fails but evidence was created, preserve the bundle and report both the failure and the evidence path.

## Workflow

1. Identify the E2E command from package scripts, test config, project docs, or the user's request.
2. Ensure video recording is enabled before running tests.
3. Run the command through `scripts/collect_e2e_video_evidence.py`.
4. Inspect `SUMMARY.md`, `manifest.json`, and copied artifacts.
5. Tell the user the exact evidence directory and whether videos were found.

## Enabling Video Recording

For Playwright, prefer project config over one-off flags when editing is acceptable:

```ts
use: {
  video: 'retain-on-failure',
  trace: 'retain-on-failure',
  screenshot: 'only-on-failure',
}
```

Use `video: 'on'` when the user explicitly needs proof for successful runs too. If avoiding config edits, run with environment variables or project-supported flags when available.

For Cypress, confirm `video: true` in config or use:

```bash
npx cypress run --config video=true
```

For browser automation outside Playwright/Cypress, use the tool's native video or screen-recording option if it exists. If no video support exists, collect screenshots, traces, logs, and a clear note that video recording was unavailable.

## Collector Usage

Run from the target project root:

```bash
python3 /path/to/e2e-video-evidence/scripts/collect_e2e_video_evidence.py [options] -- <e2e command>
```

Useful options:

- `--output-dir DIR`: evidence root, default `e2e-evidence`.
- `--name NAME`: readable run name used in the evidence folder.
- `--include PATTERN`: extra glob to collect, repeatable.
- `--max-file-mb N`: skip files larger than this size, default 500.
- `--no-copy`: write manifest and logs without copying artifacts.

Default collected extensions include `.webm`, `.mp4`, `.mov`, `.mkv`, `.zip`, `.png`, `.jpg`, `.jpeg`, `.json`, `.html`, and `.xml` when they are in common E2E artifact locations or were modified during the run.

## Reporting Standard

In the final response, include:

- Test command and pass/fail status.
- Evidence directory as an absolute path.
- Count and names of video files found.
- Any limitation, such as video recording not being enabled.

Keep the bundle even when tests fail. Failure videos are often the most useful evidence.
