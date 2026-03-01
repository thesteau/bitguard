import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..environments import environments as envs
from app.utils.template_decorator import template

router = APIRouter()


@router.get("/blog", response_class=HTMLResponse)
@template("pages/blog.html")
async def blog(request: Request):
    df = pd.read_csv(envs.BLOG_LINKS)
    data = {
        "blog_data": df.to_dict(orient="records")
    }

    return {
        "data": data
    }
