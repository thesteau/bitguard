import random
import json

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import requests
import redis

from ..environments import environments as envs


r = redis.Redis(host="redis", port=6379, decode_responses=True)

MAX_ADDRESS_LEN = 120
ALLOWED_DEPTHS = {0, 1, 2, 3}
BACKEND_URL = envs.BACKEND_URL

router = APIRouter()


class SubmitRequest(BaseModel):
    seed_parameter: str = Field(min_length=1)
    depth: int = 0


def validate_address(seed_parameter: str, depth: int):
    # Placeholder for real validation logic
    # Request send to link

    recommendation = "DO_NOT_SEND"
    risk_score = 85
    predicted_type = "RANSOMWARE"
    confidence = 0.95

    try:
        res = requests.post(f"{BACKEND_URL}/validate", json={"seed_parameter": seed_parameter, "depth": depth})
        if res.status_code == 200:
            data = res.json()
            risk_score = data.get("risk_score", risk_score)
            predicted_type = data.get("predicted_type", predicted_type)
            confidence = data.get("confidence", confidence)

            if risk_score >= 80:
                recommendation = "DO_NOT_SEND"
            elif risk_score >= 50:
                recommendation = "CAUTION"
            else:
                recommendation = "SAFE"
    except:
        # In case of any error, return the default mocked values
        pass

    return risk_score, predicted_type, confidence, recommendation


async def validate_address_mock(seed_parameter: str, depth: int):
    # Mock validation logic: 90% chance of being valid
    # ---- MOCK LOGIC ----
    print(seed_parameter)
    json_data = {}
    try:
        res = requests.post(f"{BACKEND_URL}/validate", json={"seed_parameter": seed_parameter, "depth": depth})
        json_data = res.json()  # Simulate processing the response
        print("This is the json data", json_data)
        print(res.text)
    except:
        print("Error connecting to backend for validation, using mock values")

    mocked_types = [
        "RANSOMWARE",
        "UNKNOWN",
        "OKAY",
    ]

    predicted_type = random.choice(mocked_types)
    risk_score = len(json_data) if json_data else 50  # Default if empty
    confidence = round(random.uniform(0.60, 0.99), 2)

    if risk_score >= 80:
        recommendation = "DO_NOT_SEND"
    elif risk_score >= 50:
        recommendation = "CAUTION"
    else:
        recommendation = "SAFE" + f" {risk_score}"
    return risk_score, predicted_type, confidence, recommendation


def is_allowed_address(address: str) -> bool:
    a = address.strip().lower()

    if not a:
        return False

    if len(a) > MAX_ADDRESS_LEN:
        return False

    return a.startswith("bc1") or a.startswith("1") or a.startswith("3")


@router.post("/submit")
async def submit(req: SubmitRequest):
    seed_parameter = req.seed_parameter.strip().lower()
    depth = req.depth

    if not seed_parameter:
        raise HTTPException(status_code=400, detail="Seed parameter is required")

    if not (seed_parameter.startswith("bc1") or seed_parameter.startswith("1") or seed_parameter.startswith("3")):
        raise HTTPException(status_code=400, detail="Seed parameter must start with bc1, 1, or 3")

    cache_key = f"btc:{seed_parameter}:{depth}"

    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    risk_score, predicted_type, confidence, recommendation = await validate_address_mock(seed_parameter, depth)

    result = {
        "risk_score": risk_score,
        "predicted_type": predicted_type,
        "confidence": confidence,
        "recommendation": recommendation
    }

    r.setex(cache_key, 259200, json.dumps(result))

    return result
