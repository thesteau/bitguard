from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter()


class ValidationFeatures(BaseModel):
    in_degree: float
    out_degree: float
    total_degree: float
    total_received_btc: float
    total_sent_btc: float
    avg_received_btc: float
    avg_sent_btc: float
    balance: float
    equal_output_count: float
    suspicious_blocks: float
    max_equal_outputs: float
    fan_in_out_ratio: float
    lifetime_blocks: float
    tx_frequency: float
    dust_tx_count: float
    dust_ratio: float
    round_number_ratio: float
    amount_variance: float
    has_dust_attack: float
    has_round_laundering: float


@router.get("/")
def read_root():
    return {"message": "Hello, World!"}


@router.post("/")
def create_root(request: Request):
    print("Received POST request at / with body:", request.body())
    # For debugging requests from the frontend
    return {"message": "Hello, World!"}


# Model route
@router.post("/validate")
def validate_address(payload: ValidationFeatures, request: Request):
    model = request.app.state.bitguard_model
    score = model.predict_from_features(payload.model_dump())
    return {"status": "ok", "score": score}
