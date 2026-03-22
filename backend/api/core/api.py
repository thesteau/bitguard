import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from model.loader import lgb_model, scale_loader
from core.routers import include_routers


app = FastAPI()

app.state.bitguard_model = lgb_model
app.state.bitguard_scaler = scale_loader


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

include_routers(app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8444)
