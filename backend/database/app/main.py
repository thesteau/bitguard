import os
from fastapi import FastAPI, Request
from pathlib import Path
from neo4j import GraphDatabase
from .environments import environments as envs

app = FastAPI()

DATABASE = envs.NEO4J_DATABASE


# Create neo4j driver
driver = GraphDatabase.driver(
    envs.NEO4J_URI,
    auth=(
        envs.NEO4J_USERNAME,
        envs.NEO4J_PASSWORD,
    ),
)
query = Path("queries/base_query.cypher").read_text(encoding="utf-8")


@app.post("/query")
async def query_database(request: Request):
    parameter = await request.json()

    with driver.session(database=DATABASE) as session:
        result = session.run(query, parameter)
        records = [record.data() for record in result]

    return records
