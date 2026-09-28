# Backend

FastAPI backend for the restaurant waitlist manager. It uses SQLAlchemy with a
SQLite database by default and seeds demo records on first startup.

Run from this directory:

```sh
uv sync
uv run uvicorn app.main:app --reload --port 8001
uv run pytest
```

The default database URL is `sqlite:///./waitlist.db` (relative to the backend
working directory). Override it with `DATABASE_URL`, for example:

```sh
DATABASE_URL=sqlite:////absolute/path/to/waitlist.db uv run uvicorn app.main:app --reload --port 8001
```

The application uses SQLAlchemy models and sessions without SQLite-specific
queries. To use another SQLAlchemy-supported database later, configure its URL
and install the matching DBAPI driver.

Seeded demo accounts use `demo-password`:

- `claire@obermamma.fr` (manager)
- `tom@obermamma.fr` (host)

`POST /auth/login` returns an opaque bearer token. Send it as
`Authorization: Bearer <accessToken>` to protected endpoints. Passwords are
stored as scrypt hashes, and only token digests are stored in the database.
Staff created without an initial password are not able to sign in until a
password is provisioned.
