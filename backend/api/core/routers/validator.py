from fastapi import APIRouter, Request
from pydantic import BaseModel
from ..helpers.database import get_data_from_database


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


# Model route
@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    model = request.app.state.bitguard_model

    # Data base request code
    bitcoin_data = get_data_from_database(payload.model_dump())

    # Data transformation Code - Pipeline Code
    transformed_df = bitcoin_data.to_json(orient="records")  # PLACE HOLDER
    # data_transform

    # Model Code
    # result =model.predict_from_features(transformed_df)

    result = transformed_df  # PLACE HOLDER
    return result
