import random
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import requests

from ..environments import environments as envs

router = APIRouter()


class SubmitRequest(BaseModel):
    address: str = Field(min_length=1)


def validate_address(address: str):
    # Placeholder for real validation logic
    # Request send to link

    recommendation = "DO_NOT_SEND"
    risk_score = 85
    predicted_type = "RANSOMWARE"
    confidence = 0.95
    return risk_score, predicted_type, confidence, recommendation


def validate_address_mock(address: str):
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


@router.post("/submit")
async def submit(req: SubmitRequest):
    address = req.address.strip()

    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    risk_score, predicted_type, confidence, recommendation = validate_address_mock(address)

    return {
        "risk_score": risk_score,
        "predicted_type": predicted_type,
        "confidence": confidence,
        "recommendation": recommendation
    }
