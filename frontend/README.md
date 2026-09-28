# Restaurant Waitlist Manager frontend

The frontend uses the FastAPI service in `../backend` for staff, waitlist,
restaurant, analytics, and public guest operations. The API URL defaults to
`http://localhost:8001`, using the `API_PORT` variable from the root Makefile.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/95efad11-fccc-4ce8-95f5-70e3a38fb0af).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? From the repository root, install dependencies and start both services with:

```sh
make install
make dev
```
