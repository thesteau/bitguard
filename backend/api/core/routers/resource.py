from fastapi import APIRouter, Request
import requests
import ...environments.environments as envs

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Hello, World!"}


@router.post("/")
async def create_root(request: Request):
    print("Received POST request at / with body:", await request.json())
    # For debugging requests from the frontend
    return {"message": "Hello, World!"}

@router.get("/test")
async def test_connection():
    res = requests.get(f"{envs.BACKEND_URL}/test")
    if res.status_code == 200:
        print("Successfully connected to backend")
    else:
        print(f"Error connecting to backend: {res.status_code}, {res.text}")

    return res.json()
