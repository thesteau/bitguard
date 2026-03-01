from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.utils.template_decorator import template


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@template("pages/index.html")
async def index(request: Request):
    return {}


@router.get("/about", response_class=HTMLResponse)
@template("pages/about.html")
async def about(request: Request):
    return {}


@router.get("/pricing", response_class=HTMLResponse)
@template("pages/pricing.html")
async def pricing(request: Request):
    return {}


@router.get("/contact", response_class=HTMLResponse)
@template("pages/contact.html")
async def contact(request: Request):
    return {}


@router.get("/privacy", response_class=HTMLResponse)
@template("pages/privacy.html")
async def privacy(request: Request):
    return {}


@router.get("/login", response_class=HTMLResponse)
@template("pages/login.html")
async def login(request: Request):
    return {}
