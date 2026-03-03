from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import include_routers
from app.errors.handlers import register_exception_handlers

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.templates = Jinja2Templates(directory="templates")

include_routers(app)  # pull everything from routers in one call

register_exception_handlers(app)
