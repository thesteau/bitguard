import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.helpers.transact_database import get_data_from_database
from app.helpers.model_prediction import predict_score
from pipeline_code.bitcoin_fraud_pipeline import build_features


router = APIRouter()
logger = logging.getLogger(__name__)


class ValidationRequest(BaseModel):
    seed_parameter: str
    depth: int = 0


@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    model = request.app.state.bitguard_model
    scaler = request.app.state.bitguard_scaler

    logger.info("INFO: Received validation request for seed_parameter: %s, depth: %s",
                payload.seed_parameter, payload.depth)

    try:
        bitcoin_data = get_data_from_database(payload.model_dump())
    except Exception as e:
        logger.error("ERROR: Error occurred while fetching data: %s", str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching data: {str(e)}") from e

    if bitcoin_data is None or bitcoin_data.empty:
        logger.error("ERROR: No data found for the given parameters.")
        raise HTTPException(status_code=404, detail="No data found for the given parameters.")

    transformed_df = build_features(bitcoin_data)
    X_scaled = scaler.transform(transformed_df)

    result = predict_score(model, X_scaled)
    return {"score": result}
