# AGENTS.md

This file provides guidance to Codex when working with code in this repository.

## Project Overview

A web-based scholarship and research-opportunity tool. The system searches and filters scholarships and research programs (REUs, fellowships, lab internships) against a student profile (GPA, university, major, heritage, first-gen status, skills, etc.) and lets students download results as CSV / Excel / PDF / ICS calendar / application tracker.

**Author:** Tim Smith  
**License:** All code owned by Tim  
**Production host:** Vercel (project `scholarship-vercel`), sourced from the GitHub repository `mantux07/scholarship-api`. Live at **https://scholarships.tsprofits.com**.

## Current Deployment Model

The source of truth is the GitHub repo:

```text
https://github.com/mantux07/scholarship-api
```

Vercel hosts the app and auto-deploys from the repo. Treat `main` as the production branch unless Tim says otherwise. Use `dev` for staging and local validation before merging into `main`.

- **Production URL:** https://scholarships.tsprofits.com (custom domain aliased to the Vercel project `scholarship-vercel`).
- Pushing to `main` triggers an automatic Vercel build/deploy. You can also deploy/redeploy with the authenticated `vercel` CLI.
- Verify deploy status with `vercel ls scholarship-vercel` (look for `● Ready` + the expected commit) and `vercel inspect --logs <url>` for build failures. Trust the pipeline over `curl`: Vercel's bot protection ("Vercel Security Checkpoint" / Attack Challenge Mode) can serve a 403/JS-challenge page to automated requests after rapid probing, which blocks `curl`/WebFetch verification but does not affect real browser visitors.
- GoDaddy is **not** the host. Earlier notes claiming GoDaddy production were incorrect.

## Architecture

Everything lives in `scholarship-vercel/`, which matches the Vercel project name.

```text
scholarship_system/
├── AGENTS.md
├── CLAUDE.md
├── README.md
└── scholarship-vercel/
    ├── vercel.json              # Vercel build config (Python build + weekly cron)
    ├── requirements.txt         # Flask, Flask-CORS, openpyxl, reportlab, anthropic, requests
    └── api/
        ├── index.py             # Flask app: search, research, downloads, email, cron
        ├── scholarship_research_agent_dynamic.py
        ├── research_opportunity_agent.py
        ├── scholarship_output_modules.py
        ├── claude_suggestions.py
        ├── kv_store.py
        ├── email_client.py
        └── static/
            ├── index.html
            ├── app.js
            └── styles.css
```

There is no active CLI tool, no `webapp/` directory, and no Render deployment. Old code was removed 2026-05-25 and archived to:

```text
/Users/tsmith/Claude/_archives/scholarship_system_cleanup_2026-05-25.tar.gz
```

Do not recreate the old CLI, `webapp/`, or Render config.

## Data Flow

Browser form → `api/static/app.js` → `POST /api/search` or `POST /api/research` (or both when the "Both" tab is active) → Flask handler in `api/index.py` builds a profile dict → calls `DynamicScholarshipAgent` and/or `ResearchOpportunityAgent` → JSON response → frontend renders cards + offers downloads.

The frontend uses relative API paths (`const API_URL = '';`) so frontend and backend must be served from the same host.

## API Endpoints

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serves `static/index.html` |
| GET | `/<path:filename>` | Serves static assets |
| POST | `/api/search` | Scholarship search |
| POST | `/api/download/<format>` | Download scholarship results: `csv`, `excel`, `pdf`, `calendar`, `tracker`, `html` |
| POST | `/api/research` | Research-opportunity search |
| POST | `/api/research/download/<format>` | Download research results: `csv`, `excel`, `pdf`, `calendar`, `tracker` |
| POST | `/api/subscribe` | Save email + profile, send confirmation |
| GET | `/api/unsubscribe` | Remove email from subscriber storage |
| GET | `/api/cron` | Weekly scholarship alerts; secured by `CRON_SECRET` when set |

## Local Development

Use the Flask app directly:

```bash
cd /Users/tsmith/Claude/scholarship_system/scholarship-vercel
python3 api/index.py
```

For route-level tests, importing `api/index.py` and using Flask's `test_client()` is usually faster and avoids external hosting concerns.

## Branch Workflow

```bash
cd /Users/tsmith/Claude/scholarship_system/scholarship-vercel

git checkout dev
# edit, test, commit
git push origin dev

# after validation
git checkout main
git merge dev
git push origin main
```

Vercel auto-deploys from `main`. A push to `main` produces a new production build that is aliased to https://scholarships.tsprofits.com on success.

## Environment Variables

Set environment variables in the Vercel project (dashboard or `vercel env add`), not in committed files:

- `ANTHROPIC_API_KEY` — enables `claude_suggestions.py`
- `KV_*` (Vercel KV) — enables email subscriber storage
- `RESEND_API_KEY` or SMTP credentials — enables email sending
- `CRON_SECRET` — gates `/api/cron` (set; the weekly cron is defined in `vercel.json`)

When setting a var via the CLI, pipe with `printf 'value'`, **not** `echo "value"` — `echo` appends a trailing newline, and Vercel rejects whitespace in `CRON_SECRET` at build time, which silently fails every subsequent deploy with `● Error`.

All optional clients should fail gracefully if env vars are absent; local database search must still work.

## Important Input Handling

The app must use the current submitted form data for every search. Do not silently default the student's major to Engineering, Computer Science, STEM, or any other degree. Missing or blank required fields should return validation errors instead of inventing profile values.

This was fixed on 2026-06-02 after the site appeared to reference Engineering for all searches.

## Frontend Tabs

Three tabs at the top of the page: **Scholarships | Research | Both**. The active tab determines whether the submit handler calls `/api/search`, `/api/research`, or both in parallel.

## When Making Changes

- Work from `scholarship-vercel/`; the name matches the Vercel project.
- Prefer local Flask route tests before pushing.
- Push fixes to `dev` first when practical, then merge to `main` after validation.
- Do not add a second deployment target (e.g. GoDaddy, Render) unless Tim explicitly asks.
