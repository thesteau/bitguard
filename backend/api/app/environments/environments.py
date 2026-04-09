import os

MODEL_PATH = os.getenv("MODEL_PATH", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
SCALER_PATH = os.getenv("SCALER_PATH", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
X402_ENABLED = os.getenv("X402_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
X402_PAY_TO_ADDRESS = os.getenv("X402_PAY_TO_ADDRESS", "")
X402_NETWORK = os.getenv("X402_NETWORK", "eip155:84532")
X402_PRICE = os.getenv("X402_PRICE", "$0.001")
X402_PROTECTED_ROUTE = os.getenv("X402_PROTECTED_ROUTE", "POST /validate")
X402_DESCRIPTION = os.getenv("X402_DESCRIPTION", "Access to wallet validation API")
X402_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://x402.org/facilitator")
