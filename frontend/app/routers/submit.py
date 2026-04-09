import json
import logging

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import requests
import redis

from ..environments import environments as envs

router = APIRouter()

redis_caching = redis.Redis(host="redis", port=6379, decode_responses=True)
logger = logging.getLogger(__name__)

MAX_ADDRESS_LEN = 120
BACKEND_URL = envs.BACKEND_URL
INTERNAL_API_KEY = envs.INTERNAL_API_KEY


class SubmitRequest(BaseModel):
    seed_parameter: str = Field(min_length=1)


async def validate_address(seed_parameter: str):
    response = None

    try:
        response = requests.post(
            f"{BACKEND_URL}/validate",
            json={"seed_parameter": seed_parameter},
            headers={"X-Internal-API-Key": INTERNAL_API_KEY},
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error("ERROR: Error connecting to validation backend: %s", str(exc))

        backend_detail = None
        backend_status = response.status_code if response is not None else None

        if response is not None:
            try:
                backend_detail = response.json().get("detail")
            except ValueError:
                backend_detail = response.text or None

        if backend_status is not None:
            if backend_status >= 500:
                logger.error("ERROR: Backend error: %s - %s", backend_status, backend_detail or "")
                raise HTTPException(
                    status_code=502,
                    detail=backend_detail or f"Backend error: {backend_status}, try again later or contact us."
                ) from exc

            raise HTTPException(
                status_code=backend_status,
                detail=backend_detail or "Error validating request."
            ) from exc

        raise HTTPException(
            status_code=502,
            detail="Error validating request, try again later or contact us."
        ) from exc

    return response.json()


def is_allowed_address(address: str):
    a = address.strip()

    if not a:
        return False

    if len(a) > MAX_ADDRESS_LEN:
        return False

    return a.startswith("bc1") or a.startswith("1") or a.startswith("3")


@router.post("/submit")
async def submit(req: SubmitRequest):
    seed_parameter = req.seed_parameter.strip()

    if not seed_parameter:
        raise HTTPException(status_code=400, detail="Seed parameter is required")

    if not (seed_parameter.startswith("bc1") or seed_parameter.startswith("1") or seed_parameter.startswith("3")):
        raise HTTPException(status_code=400, detail="Seed parameter must start with bc1, 1, or 3")

    cache_key = f"btc:{seed_parameter}"

    cached = redis_caching.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await validate_address(seed_parameter)

    redis_caching.setex(cache_key, 259200, json.dumps(result))

    return result
