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

`FRONTEND_PORT` serves the React app (default `3002`). `API_PORT` serves the
FastAPI backend (default `8001`), which is the API the frontend calls. They
are separate ports: `make dev API_PORT=8002` leaves the frontend on 3002 and
starts the backend on 8002, so the frontend calls port 8002.

The backend stores data in `backend/waitlist.db` by default. Set `DATABASE_URL`
to choose a different SQLAlchemy database URL.

Run only one service with `make frontend` or `make backend`. Run the backend
tests with `make test`. Set `API_PORT=8000` if you want the backend to use a
different port.

The frontend calls the FastAPI backend. Set `FRONTEND_ORIGINS` for additional
frontend origins. The local demo accounts use password
`demo-password`; see [backend/README.md](backend/README.md) for details.
