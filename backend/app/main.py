from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db import close_db, init_db
from .routers import auth, dashboard, invoices, products, sales


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield
    close_db()


app = FastAPI(title="StockLens API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    """The frontend shows `detail` as text, so turn pydantic's list into one readable sentence."""
    parts = []
    for err in exc.errors():
        field = next((str(p) for p in reversed(err.get("loc", ())) if p not in ("body", "query")), "request")
        parts.append(f"{field.replace('_', ' ')}: {err.get('msg', 'invalid value')}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request."})


@app.get("/api/health")
def health():
    return {"status": "ok"}


for module in (auth, products, sales, invoices, dashboard):
    app.include_router(module.router)


if __name__ == "__main__":  # lets `python -m app.main` start the server too
    import os

    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)