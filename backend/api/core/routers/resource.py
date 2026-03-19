from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Hello, World!"}


@router.post("/")
def create_root(request: Request):
    print("Received POST request at / with body:", request.body())
    # For debugging requests from the frontend
    return {"message": "Hello, World!"}
