---
name: e2e-video-evidence
description: Capture, preserve, and display evidence for E2E test runs, especially logged-in browser flows and browser test videos. Use when Codex is asked to run E2E tests, verify authenticated UI flows with video proof, use the computer-use:computer-use skill for logged-in screen inspection, leave evidence of an executed video test, show videos inline in the final response, collect Playwright/Cypress recordings, or produce a timestamped bundle containing test logs, videos, traces, screenshots, reports, and a manifest.
---

# E2E Video Evidence

Use this skill whenever an E2E run should leave auditable evidence. The expected output is a timestamped evidence directory containing the command log, manifest, generated videos, traces, screenshots, reports, an inline-display snippet, and a concise summary for the user.

## Quick Start

Prefer the bundled collector when the E2E command is known:

```bash
python3 /path/to/e2e-video-evidence/scripts/collect_e2e_video_evidence.py -- npm run test:e2e
```

The collector:

- Runs the command from the current project directory.
- Saves stdout/stderr to `e2e-evidence/<timestamp>-<command>/run.log`.
- Copies new or modified evidence files into `artifacts/`.
- Writes `manifest.json`, `SUMMARY.md`, and `DISPLAY.md`.
- Exits with the wrapped command's exit code.

If the command fails but evidence was created, preserve the bundle and report both the failure and the evidence path.

## Workflow

1. Identify the E2E command from package scripts, test config, project docs, or the user's request.
2. If the user asks for logged-in evidence, load and use `$computer-use:computer-use` from `/Users/kimurataiyou/.codex/plugins/cache/openai-bundled/computer-use/1.0.793/skills/computer-use/SKILL.md`, then inspect the real logged-in screen with Computer Use on Chrome or another allowed app before or after the run. Do not use Computer Use on apps that the runtime blocks.
3. Ensure video recording is enabled before running tests.
4. Run the command through `scripts/collect_e2e_video_evidence.py`.
5. Inspect `SUMMARY.md`, `DISPLAY.md`, `manifest.json`, and copied artifacts.
6. Tell the user the exact evidence directory, whether a logged-in screen was confirmed, and whether videos were found.

## Logged-In Screen Evidence

When the flow depends on authentication, evidence must show the post-login product surface, not only a login form or blank page.

- Prefer an existing authenticated browser profile, app session, or Playwright storage state rather than asking the user for credentials.
- Always use `$computer-use:computer-use` for logged-in visual confirmation when the user explicitly asks for a logged-in view or when authentication state is visually important.
- Use Computer Use to inspect the logged-in screen through an allowed app such as Chrome. If the target app is blocked by Computer Use safety rules, use an allowed browser/app surface and state the limitation.
- Record a durable, non-secret signal in the final response, such as the page title, visible workspace name, account avatar presence, dashboard heading, or authenticated navigation.
- Never expose passwords, tokens, session cookies, API keys, or private account details in logs or summaries.
- If authentication cannot be confirmed, say so and mark the evidence as not logged-in-confirmed.

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

## Displaying Videos Inline

Do not only hand the user a file path when a video exists. Use `DISPLAY.md` as the paste-ready source for the final response. It contains absolute-path Markdown embeds like:

```markdown
![E2E evidence video](/absolute/path/to/video.webm)
```

In Codex desktop responses, use that same Markdown image syntax for local videos so the user can view the evidence inline. If a browser cannot play the raw `.webm`, still include the inline embed and mention the codec limitation. If `ffmpeg` is available, convert a non-rendering `.webm` to `.mp4` and embed the `.mp4`.

## Reporting Standard

In the final response, include:

- Test command and pass/fail status.
- Evidence directory as an absolute path.
- Logged-in screen confirmation when relevant.
- Count and names of video files found.
- Inline video embed from `DISPLAY.md`, not only a file path.
- Any limitation, such as video recording not being enabled.

Keep the bundle even when tests fail. Failure videos are often the most useful evidence.
