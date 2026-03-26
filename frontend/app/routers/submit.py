import random
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
ALLOWED_DEPTHS = {0, 1, 2, 3}
BACKEND_URL = envs.BACKEND_URL


class SubmitRequest(BaseModel):
    seed_parameter: str = Field(min_length=1)
    depth: int = 0


def validate_address(seed_parameter: str, depth: int):
    try:
        res = requests.post(
            f"{BACKEND_URL}/validate",
            json={"seed_parameter": seed_parameter, "depth": depth},
            timeout=30
        )
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        if res.status_code >= 500:
            logger.error("ERROR: Backend error: %s - %s", res.status_code, res.text)
            raise HTTPException(status_code=502,
                                detail=f"Backend error: {res.status_code}, try again later or contact us."
                                ) from e

        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to validation backend: {str(e)}"
        ) from e

    data = res.json()
    risk_score = data["risk_score"]
    predicted_type = data["predicted_type"]
    confidence = data["confidence"]

    if risk_score >= 80:
        recommendation = "DO_NOT_SEND"
    elif risk_score >= 50:
        recommendation = "CAUTION"
    else:
        recommendation = "SAFE"

    return risk_score, predicted_type, confidence, recommendation


async def validate_address_mock(seed_parameter: str, depth: int):
    # ---- MOCK LOGIC ----
    try:
        res = requests.post(
            f"{BACKEND_URL}/validate",
            json={"seed_parameter": seed_parameter, "depth": depth},
            timeout=30
        )
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        if res.status_code >= 500:
            logger.error("ERROR: Backend error: %s - %s", res.status_code, res.text)
            raise HTTPException(status_code=502,
                                detail=f"Backend error: {res.status_code}, try again later or contact us."
                                ) from e

        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to validation backend: {str(e)}"
        ) from e

    json_data = res.json()

    mocked_types = [
        "RANSOMWARE",
        "UNKNOWN",
        "OKAY",
    ]

    predicted_type = random.choice(mocked_types)
    risk_score = len(json_data) if json_data else 50
    confidence = round(random.uniform(0.60, 0.99), 2)

    if risk_score >= 80:
        recommendation = "DO_NOT_SEND"
    elif risk_score >= 50:
        recommendation = "CAUTION"
    else:
        recommendation = "SAFE" + f" {risk_score}"
    return risk_score, predicted_type, confidence, recommendation


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
    depth = req.depth

    if not seed_parameter:
        raise HTTPException(status_code=400, detail="Seed parameter is required")

    if not (seed_parameter.startswith("bc1") or seed_parameter.startswith("1") or seed_parameter.startswith("3")):
        raise HTTPException(status_code=400, detail="Seed parameter must start with bc1, 1, or 3")

    cache_key = f"btc:{seed_parameter}:{depth}"

    cached = redis_caching.get(cache_key)
    if cached:
        return json.loads(cached)

    risk_score, predicted_type, confidence, recommendation = await validate_address_mock(seed_parameter, depth)

    result = {
        "risk_score": risk_score,
        "predicted_type": predicted_type,
        "confidence": confidence,
        "recommendation": recommendation
    }

    redis_caching.setex(cache_key, 259200, json.dumps(result))

    return result
