# Restaurant Waitlist Manager

## Quick start

Install the dependencies and start both development servers:

```sh
make install
make dev
```

Open the frontend at <http://localhost:3000>. The FastAPI backend and its
interactive OpenAPI docs are at <http://localhost:8000> and
<http://localhost:8000/docs>.

Run only one service with `make frontend` or `make backend`. Run the backend
tests with `make test`.

The frontend currently uses its local mock API; `make dev` starts the backend
alongside it, but the frontend has not yet been switched to call the backend.
See [backend/README.md](backend/README.md) for demo login details.
