from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.helpers.transact_database import get_data_from_database
from app.helpers.model_prediction import predict_score
from pipeline_code.bitcoin_fraud_pipeline import build_features


router = APIRouter()


class ValidationRequest(BaseModel):
    seed_parameter: str
    depth: int = 0


@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    model = request.app.state.bitguard_model
    scaler = request.app.state.bitguard_scaler

    try:
        bitcoin_data = get_data_from_database(payload.model_dump())
    except Exception as e:
        return {"error": f"An error occurred while fetching data: {str(e)}"}

    if bitcoin_data is None:
        # Maybe raise error?
        return {"error": "No data found for the given parameters."}

    transformed_df = build_features(bitcoin_data)
    X_scaled = scaler.transform(transformed_df)

    result = predict_score(model, X_scaled)
    return {"score": result}
