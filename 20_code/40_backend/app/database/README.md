# `app.database` — database abstraction (extension point)

A deliberately small abstraction so a successor can add persistence without
restructuring the app. Code depends only on the `DatabaseBackend` interface and
obtains an instance via `get_database()`; the backend is chosen by `.env`
(`DATABASE_BACKEND`).

> **Status:** only `none` (the `NullDatabaseBackend`) is implemented. No ORM is
> pulled in yet because there is no data model. `sqlite`, `postgres` and `d1`
> are configured in `.env` and reserved here as documented slots.

## Backends

| `DATABASE_BACKEND` | Status | Config in `.env` |
|--------------------|--------|------------------|
| `none` | Implemented (no-op) | — |
| `sqlite` | Extension point | `DATABASE_URL=sqlite:///./data/app.db` |
| `postgres` | Extension point | `DATABASE_URL=postgresql://user:pass@host:5432/db` |
| `d1` | Extension point | `D1_ACCOUNT_ID`, `D1_DATABASE_ID`, `D1_API_TOKEN` |

## Adding a backend

Mirror `app.storage` (project_rules.md §20):

1. Implement `app/database/<name>.py` subclassing `DatabaseBackend`.
   - For `sqlite`/`postgres`, SQLAlchemy is the suggested engine: read
     `DATABASE_URL` from settings and expose sessions. Add `sqlalchemy`
     (and `psycopg[binary]` for Postgres) to `requirements.txt`.
   - For `d1`, talk to the Cloudflare D1 HTTP API using the `D1_*` settings.
2. Wire it into `build_database()` in `factory.py` (lazy-import the engine).
3. Keep it stateless: open connections per request/task, do not cache sessions
   in module globals (project_rules.md §18).
4. Update this table.
