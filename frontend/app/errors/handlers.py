from fastapi import Request


async def not_found(request: Request, exc):
    templates = request.app.state.templates
    return templates.TemplateResponse("error/404.html", {"request": request}, status_code=404)


async def internal_error(request: Request, exc):
    templates = request.app.state.templates
    return templates.TemplateResponse("error/500.html", {"request": request}, status_code=500)


def register_exception_handlers(app):
    app.add_exception_handler(404, not_found)
    app.add_exception_handler(500, internal_error)
