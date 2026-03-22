from fastapi import APIRouter, Request
from pydantic import BaseModel
from ..helpers.database import get_data_from_database
from pipeline_code.bitcoin_fraud_pipeline import build_features
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


class ValidationRequest(BaseModel):
    seed_parameter: str
    depth: int = 0


@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    model = request.app.state.bitguard_model
    scaler = request.app.state.bitguard_scaler

 
    bitcoin_data = get_data_from_database(payload.model_dump())

    
    

    transformed_df = build_features(bitcoin_data)
    X_scaled = scaler.transform(transformed_df)


    result = int(((1 - model.predict_proba(X_scaled)[:, 1]) * 100).round().astype(int)[0])
    return {"score": result}

    