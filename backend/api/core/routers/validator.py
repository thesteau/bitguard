from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.helpers.database import get_data_from_database
from core.helpers.model_prediction import predict_score
from pipeline_code.bitcoin_fraud_pipeline import build_features


router = APIRouter()


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

    result = predict_score(model, X_scaled)
    return {"score": result}
