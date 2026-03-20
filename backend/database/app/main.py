import os
from fastapi import FastAPI, Request
from pathlib import Path
from neo4j import GraphDatabase
from .environments import environments as envs

app = FastAPI()

DATABASE = envs.NEO4J_DATABASE
query = Path("queries/base_query.cypher").read_text(encoding="utf-8")


# Create driver once
driver = GraphDatabase.driver(
    envs.NEO4J_URI,
    auth=(
        envs.NEO4J_USERNAME,
        envs.NEO4J_PASSWORD,
    ),
)

@app.get("/test")
async def test_connection():
    return {"message": "Connection to database successful!"}

@app.get("/test2")
async def test_connection2():
    parameters = {"seed_parameter": envs.TEST_SEED}
    with driver.session(database=DATABASE) as session:
        result = session.run(query, parameters)
        records = [record.data() for record in result]

    return {"records": records}

@app.post("/query")
async def query_database(request: Request):
    body = await request.json()
    parameters = body.get("parameters", {})

    with driver.session(database=DATABASE) as session:
        result = session.run(query, parameters)
        records = [record.data() for record in result]

    return {"records": records}
