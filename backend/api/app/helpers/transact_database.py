import requests
import pandas as pd

from app.environments import environments as envs


def get_data_from_database(payload):
    res = requests.post(f"{envs.DATABASE_URL}/query", json=payload)
    if res.status_code == 200:
        print("Successfully connected to backend")
    else:
        print(f"Error connecting to backend: {res.status_code}, {res.text}")

    df = pd.read_json(res.text)
    return df
