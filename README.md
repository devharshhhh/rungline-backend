# Rungline Backend — Phase 1

Minimal working vertical slice: fetch a problem → submit code → Judge0 runs it
against test cases → result saved to DB. This is intentionally the smallest
possible thing that proves the core loop works, matching Phase 1 of the
project doc. No auth, no adaptive engine, no AI tutor yet — those come next,
once this loop is solid.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set JUDGE0_API_KEY to a real key from
# https://rapidapi.com/judge0-official/api/judge0-ce (free tier available)
```

## Get a Judge0 key (required before code submission works)

1. Go to https://rapidapi.com/judge0-official/api/judge0-ce
2. Subscribe to the free tier (no cost, limited daily requests)
3. Copy your API key from the RapidAPI dashboard
4. Paste it into `.env` as `JUDGE0_API_KEY`

Without this, `/problems/*` endpoints work fine (they're just reading your
own DB), but `/attempts/submit` will return a clean 502 error telling you
the key is missing/invalid — it won't crash.

## Load problems into the database

1. Generate problems using the prompt in `Question_Generation_Kit.md`
2. Validate them: `python validate_problems.py problem_bank/`
3. Fix anything the validator flags as an ERROR (warnings are optional)
4. Load them in: `python seed_problems.py problem_bank/`

Name your JSON files with numeric prefixes (`01_topic.json`, `02_topic.json`)
so topics load in the order you want students to see them.

## Run the server

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API docs (auto-generated
by FastAPI — try every endpoint from the browser without writing any client
code).

## Endpoints so far

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Sanity check |
| GET | `/problems/{problem_id}` | Get one problem |
| GET | `/problems/next/{user_id}?language=python` | Next unsolved problem, sequential order (Phase 1 only — replaced by adaptive engine in Phase 2) |
| POST | `/attempts/submit` | Run submitted code against a problem's test cases, log the attempt |

## What's deliberately NOT here yet

- Authentication (there's no login — you pass a `user_id` directly for now;
  create test users straight in the DB or via a quick script)
- The adaptive engine (grade/rank movement) — Phase 2, once there's real
  attempt data to tune the mastery formula against
- The AI tutor / hints — Phase 3
- C++ support — the `LANGUAGE_IDS` map in `judge0_client.py` already has the
  Judge0 language ID for it, just needs test-case JSON generated for C++ too

## Known limitation to fix soon

The validator requires 2+ test cases per problem, but pure "print fixed
text" problems (no input) only need one meaningful check. Either loosen
that rule in `validate_problems.py` for zero-input problems, or just
duplicate the single test case (what the sample problems here do) — fine
for now, worth a proper fix before generating hundreds of these.

## Switching to Postgres later

Just change `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/rungline
```
Install `psycopg2-binary` and nothing else changes — SQLAlchemy handles the rest.
