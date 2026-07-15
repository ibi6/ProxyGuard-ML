from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import data as data_api
from app.api import experiments as experiments_api
from app.api import predict as predict_api
from app.api import settings as settings_api
from app.api import train as train_api
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ProxyGuard ML",
    version="0.2.0",
    description=(
        "Encrypted proxy traffic recognition with ensemble learning. "
        "Side-channel flow features only — no payload decryption."
    ),
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# REST APIs (must not collide with HTML page routes)
app.include_router(data_api.router)
app.include_router(train_api.router)
app.include_router(predict_api.router)
app.include_router(experiments_api.router)
app.include_router(settings_api.router)


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
    return {"status": "ok", "service": "ProxyGuard ML"}


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
