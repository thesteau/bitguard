import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.helpers.transact_database import get_data_from_database
from pipeline_code.pipeline import build_features
from app.stats import wallet_stats, risk_prob, shap_explainer


router = APIRouter()
logger = logging.getLogger(__name__)


class ValidationRequest(BaseModel):
    seed_parameter: str


@router.post("/validate")
async def validate_address(payload: ValidationRequest, request: Request):
    logger.info("INFO: Received validation request for seed_parameter: %s", payload.seed_parameter)

    model = request.app.state.bitguard_model
    shap_explainer_tree = request.app.state.shap_tree

    request_data = payload.model_dump()

    # Extract
    try:
        bitcoin_data = get_data_from_database(request_data)
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

    # Score aggregation
    risk_proba = risk_prob.prob_to_risk(result)

    wallet_stats_res = wallet_stats.compute_wallet_stats(bitcoin_data)
    risk_probability = {
        "risk_probability": risk_proba,
        "risk_score": result
    }

    reasons = shap_explainer.get_shap_explanations(transformed_df, shap_explainer_tree, risk_proba, top_n=3)

    # Return result composition
    return_result = {
        "bitcoin_wallet": payload.seed_parameter,
        "top_reasons": reasons
    }

    # Merge dictionary results
    return_result |= wallet_stats_res | risk_probability

    return return_result
