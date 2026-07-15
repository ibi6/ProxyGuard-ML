import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import data as data_api
from app.api import experiments as experiments_api
from app.api import predict as predict_api
from app.api import settings as settings_api
from app.api import train as train_api
from app.config import USE_MOCK
from app.db import init_db
from app.security import auth_required

logger = logging.getLogger("proxyguard")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [proxyguard] %(message)s",
)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Lightweight access log for demo troubleshooting (method path status ms)."""

    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        # Skip noisy static assets
        path = request.url.path
        if not path.startswith("/static"):
            ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                path,
                response.status_code,
                ms,
            )
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if USE_MOCK:
        # Visible warning for thesis demos — never present mock metrics as real.
        print(
            "[ProxyGuard] WARNING: USE_MOCK=true — training/metrics may be simulated. "
            "Unset USE_MOCK for real sklearn/xgboost runs."
        )
    if auth_required():
        print("[ProxyGuard] Write APIs require header X-API-Token (PROXYGUARD_TOKEN is set).")
    yield


app = FastAPI(
    title="ProxyGuard ML",
    version="0.2.2",
    description=(
        "Encrypted proxy traffic recognition with ensemble learning. "
        "Side-channel flow features only — no payload decryption. "
        "Default datasets are synthetic and reproducible."
    ),
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.add_middleware(RequestLogMiddleware)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# REST APIs (must not collide with HTML page routes)
app.include_router(data_api.router)
app.include_router(train_api.router)
app.include_router(predict_api.router)
app.include_router(experiments_api.router)
app.include_router(settings_api.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error", "type": type(exc).__name__},
    )


def _page(name: str, request: Request, active: str):
    return templates.TemplateResponse(
        name,
        {
            "request": request,
            "active": active,
            "title": "ProxyGuard ML",
        },
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ProxyGuard ML",
        "version": app.version,
        "use_mock": USE_MOCK,
        "auth_required": auth_required(),
        "data_mode": "synthetic_or_csv",
        "payload_decrypt": False,
    }


@app.get("/api/system")
def system_info():
    """Compact runtime snapshot for dashboard / defense demos."""
    from app.services.dataset_service import dataset_service
    from app.services.predict_service import predict_service
    from app.services.settings_service import settings_service
    from app.services.train_service import train_service

    summary = dataset_service.summary()
    models = train_service.list_models()
    settings = settings_service.get_settings()
    return {
        "service": "ProxyGuard ML",
        "version": app.version,
        "use_mock": USE_MOCK,
        "auth_required": auth_required(),
        "dataset": {
            "total_samples": summary.get("total_samples"),
            "source": summary.get("source"),
            "n_per_class": summary.get("n_per_class"),
            "seed": summary.get("seed"),
            "noise": summary.get("noise"),
        },
        "models_ready": models.get("count", 0),
        "best_model": models.get("best_model"),
        "predict_log_count": predict_service.count_logs(),
        "settings": {
            "random_seed": settings.get("random_seed"),
            "train_ratio": settings.get("train_ratio"),
            "val_ratio": settings.get("val_ratio"),
            "test_ratio": settings.get("test_ratio"),
        },
    }


@app.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request):
    return _page("dashboard.html", request, "dashboard")


@app.get("/data", response_class=HTMLResponse)
def page_data(request: Request):
    return _page("data.html", request, "data")


@app.get("/train", response_class=HTMLResponse)
def page_train(request: Request):
    return _page("train.html", request, "train")


@app.get("/predict", response_class=HTMLResponse)
def page_predict(request: Request):
    return _page("predict.html", request, "predict")


@app.get("/experiments", response_class=HTMLResponse)
def page_experiments(request: Request):
    return _page("experiments.html", request, "experiments")


@app.get("/settings", response_class=HTMLResponse)
def page_settings(request: Request):
    return _page("settings.html", request, "settings")
