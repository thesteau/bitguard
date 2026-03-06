import random
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import requests

from ..environments import environments as envs


MAX_ADDRESS_LEN = 120
ALLOWED_DEPTHS = {0, 1, 2, 3}


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
    return risk_score, predicted_type, confidence, recommendation


def validate_address_mock(address: str, depth: int):
    # Mock validation logic: 90% chance of being valid
    # ---- MOCK LOGIC ----
    mocked_types = [
        "RANSOMWARE",
        "UNKNOWN",
        "OKAY",
    ]

    predicted_type = random.choice(mocked_types)
    risk_score = random.randint(0, 100)
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
    address = req.address.strip()
    depth = req.depth

    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    if not is_allowed_address(address):
        raise HTTPException(
            status_code=400,
            detail="Address must start with bc1, 1, or 3"
        )

    if depth not in ALLOWED_DEPTHS:
        raise HTTPException(status_code=400, detail="Invalid depth")

    risk_score, predicted_type, confidence, recommendation = validate_address_mock(address, depth)

    return {
        "risk_score": risk_score,
        "predicted_type": predicted_type,
        "confidence": confidence,
        "recommendation": recommendation
    }
