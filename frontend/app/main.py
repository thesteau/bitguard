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
        "index.html",
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
        "blog.html",
        {"request": request, "data": data}
    )
