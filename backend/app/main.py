import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .routers import auth, public, restaurant, waitlist
from .store import create_database_engine, create_session_factory, get_database_url, initialize_database


def create_app(database_url: str | None = None) -> FastAPI:
    configured_url = database_url or get_database_url()
    engine = create_database_engine(configured_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_database(engine, session_factory)
        yield
        engine.dispose()

    application = FastAPI(
        title="Restaurant Waitlist API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.engine = engine
    application.state.session_factory = session_factory

    frontend_origins = os.environ.get(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002,http://127.0.0.1:3002",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in frontend_origins.split(",") if origin.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth.router)
    application.include_router(restaurant.router)
    application.include_router(waitlist.router)
    application.include_router(public.router)

    @application.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        del request
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content={"message": message}, headers=exc.headers)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        del request
        error = exc.errors()[0] if exc.errors() else None
        if error is None:
            message = "Invalid request."
        else:
            location = ".".join(str(part) for part in error["loc"] if part != "body")
            message = f"Invalid {location}: {error['msg']}" if location else error["msg"]
        return JSONResponse(status_code=422, content={"message": message})

    frontend_static_dir = Path(__file__).resolve().parent / "static"
    frontend_shell = frontend_static_dir / "_shell.html"
    if frontend_shell.is_file():
        frontend_static_root = frontend_static_dir.resolve()
        api_roots = {"analytics", "auth", "docs", "openapi.json", "redoc", "restaurant", "waitlist", "public"}

        @application.get("/", response_class=FileResponse, include_in_schema=False)
        def serve_frontend_root() -> FileResponse:
            return FileResponse(frontend_shell)

        @application.get("/{frontend_path:path}", response_class=FileResponse, include_in_schema=False)
        def serve_frontend_path(frontend_path: str) -> FileResponse:
            requested_path = (frontend_static_root / frontend_path).resolve()
            if not requested_path.is_relative_to(frontend_static_root):
                raise HTTPException(status_code=404, detail="Not found.")
            if requested_path.is_file():
                return FileResponse(requested_path)

            first_segment = frontend_path.split("/", maxsplit=1)[0]
            if first_segment in api_roots or Path(frontend_path).suffix:
                raise HTTPException(status_code=404, detail="Not found.")
            return FileResponse(frontend_shell)

    return application


app = create_app()
