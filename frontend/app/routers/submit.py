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
    address: str = Field(min_length=1)
    depth: int = 0


def validate_address(address: str, depth: int):
    # Placeholder for real validation logic
    # Request send to link

    recommendation = "DO_NOT_SEND"
    risk_score = 85
    predicted_type = "RANSOMWARE"
    confidence = 0.95

    try:
        res = requests.post(f"{BACKEND_URL}/validate", json={"seed_parameter": address, "depth": depth})
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


def validate_address_mock(address: str, depth: int):
    # Mock validation logic: 90% chance of being valid
    # ---- MOCK LOGIC ----

    try:
        res = requests.post(f"{BACKEND_URL}/validate", json={"seed_parameter": address, "depth": depth})
    except:
        print("Error connecting to backend for validation, using mock values")

    mocked_types = [
        "RANSOMWARE",
        "UNKNOWN",
        "OKAY",
    ]

    json_data = res.json()  # Simulate processing the response
    print(json_data)

    predicted_type = random.choice(mocked_types)
    risk_score = len(json_data)
    confidence = round(random.uniform(0.60, 0.99), 2)

    if risk_score >= 80:
        recommendation = "DO_NOT_SEND"
    elif risk_score >= 50:
        recommendation = "CAUTION"
    else:
        recommendation = "SAFE"
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
    address = req.address.strip().lower()
    depth = req.depth

    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    if not (address.startswith("bc1") or address.startswith("1") or address.startswith("3")):
        raise HTTPException(status_code=400, detail="Address must start with bc1, 1, or 3")

    cache_key = f"btc:{address}:{depth}"

    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    risk_score, predicted_type, confidence, recommendation = validate_address_mock(address, depth)

    result = {
        "risk_score": risk_score,
        "predicted_type": predicted_type,
        "confidence": confidence,
        "recommendation": recommendation
    }

    r.setex(cache_key, 259200, json.dumps(result))

    return result
