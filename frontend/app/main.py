import requests

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd

from .environments import environments as envs


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "pages/index.html",
        {"request": request}
    )


@app.get("/blog", response_class=HTMLResponse)
def blog(request: Request):
    # Get the data from google sheets
    df = pd.read_csv(envs.BLOG_LINKS)
    data = {
        "blog_data": df.to_dict(orient="records")
    }

    return templates.TemplateResponse(
        "pages/blog.html",
        {"request": request, "data": data}
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(
        "pages/about.html",
        {"request": request}
    )


@app.get("/pricing", response_class=HTMLResponse)
def pricing(request: Request):
    return templates.TemplateResponse(
        "pages/pricing.html",
        {"request": request}
    )


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(
        "pages/contact.html",
        {"request": request}
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse(
        "pages/privacy.html",
        {"request": request}
    )


@app.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    return templates.TemplateResponse(
        "pages/signup.html",
        {"request": request}
    )


@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request}
    )


@app.exception_handler(404)
def not_found(request: Request, exc):
    return templates.TemplateResponse(
        "error/404.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(500)
def internal_error(request: Request, exc):
    return templates.TemplateResponse(
        "error/500.html",
        {"request": request},
        status_code=500
    )
