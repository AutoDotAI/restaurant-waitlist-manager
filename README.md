# Restaurant Waitlist Manager

## Quick start

Install the dependencies and start both development servers:

```sh
make install
make dev
```

Open the frontend at <http://localhost:3002> (the default `FRONTEND_PORT`). The FastAPI backend and its
interactive OpenAPI docs are at <http://localhost:8001> and
<http://localhost:8001/docs>.

The backend stores data in `backend/waitlist.db` by default. Set `DATABASE_URL`
to choose a different SQLAlchemy database URL.

Run only one service with `make frontend` or `make backend`. Run the backend
tests with `make test`. Set `API_PORT=8000` if you want the backend to use a
different port.

The frontend calls the FastAPI backend. Set `VITE_API_BASE_URL` in
`frontend/.env.local` to change the API URL, and set `FRONTEND_ORIGINS` for
additional frontend origins. The local demo accounts use password
`demo-password`; see [backend/README.md](backend/README.md) for details.
