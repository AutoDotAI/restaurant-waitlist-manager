from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routers import auth, public, restaurant, waitlist
from .store import store

app = FastAPI(title="Restaurant Waitlist API", version="1.0.0")
app.state.store = store

app.include_router(auth.router)
app.include_router(restaurant.router)
app.include_router(waitlist.router)
app.include_router(public.router)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(status_code=exc.status_code, content={"message": message}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    del request
    error = exc.errors()[0] if exc.errors() else None
    if error is None:
        message = "Invalid request."
    else:
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        message = f"Invalid {location}: {error['msg']}" if location else error["msg"]
    return JSONResponse(status_code=422, content={"message": message})


def reset_database() -> None:
    """Reset the seeded in-memory store; intended for tests and local demos."""
    store.reset()
