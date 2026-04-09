import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.payments.payments import configure_x402
from model.loader import lgb_model
from app.routers import include_routers
from app.stats import shap_explainer


app = FastAPI()

app.state.bitguard_model = lgb_model
app.state.shap_tree = shap_explainer.init_explainer(app.state.bitguard_model)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_x402(app)

include_routers(app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8444)
