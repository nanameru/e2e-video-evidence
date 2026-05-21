# E2E Video Evidence Skill

Agent skill for preserving video evidence from E2E test runs.

## Install

Install with the Vercel `skills` CLI:

```bash
npx skills add nanameru/e2e-video-evidence --skill e2e-video-evidence -g -a codex
```

Or install from the repository URL:

```bash
npx skills add https://github.com/nanameru/e2e-video-evidence --skill e2e-video-evidence -g -a codex
```

## What It Does

The skill tells an agent to run E2E tests through a bundled collector script so every run leaves a timestamped evidence bundle:

- `run.log`
- `manifest.json`
- `SUMMARY.md`
- copied videos, traces, screenshots, reports, and related artifacts

## Direct Script Usage

From a project root:

```bash
python3 ~/.codex/skills/e2e-video-evidence/scripts/collect_e2e_video_evidence.py -- npm run test:e2e
```

The collector exits with the wrapped command's exit code, so it can be used in local verification and CI.

## Repository Layout

```text
skills/
  e2e-video-evidence/
    SKILL.md
    agents/openai.yaml
    scripts/collect_e2e_video_evidence.py
```

The `skills/` layout is intentionally compatible with the Vercel `skills` CLI repository discovery rules.
