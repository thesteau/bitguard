import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.helpers.transact_database import get_data_from_database
from pipeline_code.pipeline import build_features


router = APIRouter()
logger = logging.getLogger(__name__)


class ValidationRequest(BaseModel):
    seed_parameter: str


@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    model = request.app.state.bitguard_model

    logger.info("INFO: Received validation request for seed_parameter: %s", payload.seed_parameter)

    # Extract
    try:
        bitcoin_data = get_data_from_database(payload.model_dump())
    except Exception as e:
        logger.error("ERROR: Error occurred while fetching data: %s", str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching data: {str(e)}") from e

    if bitcoin_data is None or bitcoin_data.empty:
        logger.error("ERROR: No data found for the given parameters.")
        raise HTTPException(status_code=404, detail="No data found for the given parameters.")

    # Transform
    transformed_df = build_features(bitcoin_data)

    # Predict
    result = float(model.predict_proba(transformed_df)[0][1])
    return {"score": result}
