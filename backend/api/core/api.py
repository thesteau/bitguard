from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pickle

with open('bitguard_lightgbm.pkl', 'rb') as f:
    model = pickle.load(f)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# return 404 for this route
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


# Model route
@app.post("/validate")
def validate_address():
    # # X must have these columns in this order:
    # feature_cols = [
    #     'in_degree', 'out_degree', 'total_degree',
    #     'total_received_btc', 'total_sent_btc',
    #     'avg_received_btc', 'avg_sent_btc', 'balance',
    #     'equal_output_count', 'suspicious_blocks', 'max_equal_outputs', 'fan_in_out_ratio',
    #     'lifetime_blocks', 'tx_frequency',
    #     'dust_tx_count', 'dust_ratio', 'round_number_ratio', 'amount_variance',
    #     'has_dust_attack', 'has_round_laundering'
    # ]

    # # 0 = bad, 100 = safe
    # scores = model.predict_score(X)  # X must be StandardScaler-transformed
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
