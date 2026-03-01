from functools import wraps
from fastapi.responses import HTMLResponse


def template(template_name: str, status_code: int = 200):
    def decorator(route_function):

        @wraps(route_function)
        async def wrapper(*args, **kwargs):
            result = await route_function(*args, **kwargs)

            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if hasattr(arg, "app"):
                        request = arg
                        break

            templates = request.app.state.templates

            if isinstance(result, dict):
                result["request"] = request
                return templates.TemplateResponse(
                    template_name,
                    result,
                    status_code=status_code,
                )

            return result

        return wrapper

    return decorator