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
        ├── dedupe.py            # DuplicateFilter: fuzzy name / URL duplicate detection
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

### How the pieces fit

- **The "database" is Python code.** There is no data file or DB: each agent builds its catalog from hardcoded `add_*_scholarships()` / `add_*_programs()` methods that call `add_scholarship(...)` / `add_research_opportunity(...)`. Adding or fixing a listing means editing those methods. Catalog methods overlap, so both agents drop repeat listings through `dedupe.DuplicateFilter` (first one added wins; `add_scholarship` checks on insert, `ResearchOpportunityAgent._drop_duplicates` after the catalog is built). Check `LOG_LEVEL=DEBUG` output for `Skipping duplicate` lines after adding listings. Major gating uses `_is_stem_major` (all of STEM, including natural sciences; Nursing and other health majors are deliberately excluded) for SMART/Goldwater, and the narrower `_is_tech_major` (engineering/computing) for SWE and the corporate tech awards. Profile-based eligibility filtering and priority scoring happen inside the agents (`calculate_priority_score`, `ResearchOpportunity.matches_profile` / `calculate_priority`).
- **Merit-only by default.** The `financial_need` checkbox (profile key, default `False`) opts in to need-based awards. Scholarships are tagged `need_based` by `is_need_based_text` keyword matching on eligibility/notes, and dropped at the end of `research_scholarships()` unless the flag is set. Research programs with non-empty `target_identities` (McNair, LSAMP, etc.) are included only when the flag is set **and** `identity_hits(profile) > 0`. AI suggestions get the same keyword filter, and the prompt asks for merit-only. Results carry `need_based` / `restricted_eligibility` for the UI badge.
- **Deadlines are strings** parsed by `parse_deadline`. `days_until_deadline == 999` means "TBD" (serialized as `'TBD'`). Expired entries (`< 0`) are dropped in `index.py`, so a stale hardcoded deadline makes a listing disappear silently.
- **Two profile builders:** `_build_profile` (scholarships, also used by `/api/cron`) and `_build_research_profile` (research) in `index.py`. Their defaults differ. Both endpoints run `_profile_validation_error`, which requires university, major, and year.
- **AI suggestions are merged only into the search response.** `/api/search` runs the local agent, then `claude_suggestions.get_suggestions` via `_fetch_ai_suggestions` (`AI_SUGGESTIONS_TIMEOUT` = 20s; timeouts and errors fall back to database-only results), and drops suggestions that `DuplicateFilter` matches to a database entry by fuzzy name or application URL. Downloads re-run the local agent from the submitted profile, so AI-suggested items never appear in exported files.
- **Exporters are split.** Scholarship exports use the classes in `scholarship_output_modules.py`, plus `agent.export_to_csv` for CSV. Research exports are the `_research_export_*` functions inside `index.py`. Files are written to `tempfile.gettempdir()` (Vercel's writable `/tmp`).
- **Optional integrations** (`claude_suggestions`, `kv_store`, `email_client`) each expose `is_available()` based on env vars. Check it before calling them. `kv_store` talks to Vercel KV over REST through `requests`.
- **Errors and logging:** routes don't catch exceptions themselves. Raise `BadRequest(msg)` for user-facing 400s (`_json_body()` and `_require_valid()` do this). Anything else hits the global handler, which logs the traceback and returns a generic 500 without exception text. All modules log through `logging` to stdout (Vercel function logs), with one line per `/api/` request. Downloads go through `_temp_path` / `_send_temp_file`, which use a unique `/tmp` path and delete the file after reading it.
- `vercel.json` sends every route to `api/index.py` (60s `maxDuration`). The cron runs Mondays 09:00 UTC.

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

There is no test suite, linter, or build step. For route-level checks, use Flask's `test_client()`. It is faster and avoids Vercel bot protection:

```bash
cd /Users/tsmith/Claude/scholarship_system/scholarship-vercel
python3 -c "
import sys; sys.path.insert(0, 'api'); from index import app
c = app.test_client()
p = {'gpa': 3.6, 'university': 'Purdue University', 'major': 'Biology', 'year': 'Junior'}
r = c.post('/api/search', json=p); print(r.status_code, r.json['total'])
r = c.post('/api/research', json=p); print(r.status_code, r.json['total'])
"
```

Vary the major, heritage, state, and so on across checks. Results must change with the submitted profile (see Important Input Handling).

## Docs Layout

`/Users/tsmith/Claude/scholarship_system/` is not a git repo. Only `scholarship-vercel/` is. `CLAUDE.md` and `AGENTS.md` (the Codex copy, which differs only in its header) exist both at the root and inside `scholarship-vercel/`, and the copy inside `scholarship-vercel/` is the one tracked in git. Keep all four in sync. The root `README.md` is stale: it documents the removed CLI (`scholarship_agent_complete.py`, `--gpa` flags), so don't follow it.

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
- `LOG_LEVEL` — optional, default `INFO`; `DEBUG` adds skipped duplicates, raw Claude responses, export file paths
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
