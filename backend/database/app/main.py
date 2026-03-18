import os
from fastapi import FastAPI, Request
from pathlib import Path
from neo4j import GraphDatabase

app = FastAPI()

DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
query = Path("queries/base_query.cypher").read_text(encoding="utf-8")


# Create driver once
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD"),
    ),
)

@app.post("/query")
async def query_database(request: Request):
    body = await request.json()
    parameters = body.get("parameters", {})

    with driver.session(database=DATABASE) as session:
        result = session.run(query, parameters)
        records = [record.data() for record in result]

    return {"records": records}
