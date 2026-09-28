# Backend

FastAPI mock backend for the restaurant waitlist manager. The store is in memory
and resets whenever the server restarts.

Run from this directory:

```sh
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

Seeded demo accounts use `demo-password`:

- `claire@obermamma.fr` (manager)
- `tom@obermamma.fr` (host)

`POST /auth/login` returns an opaque bearer token. Send it as
`Authorization: Bearer <accessToken>` to protected endpoints. Passwords are
stored as scrypt hashes, and the in-memory store keeps only token digests.
Staff created without an initial password are not able to sign in until a
password is provisioned.
