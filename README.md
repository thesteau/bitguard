# BitGuard


## Teammates
-
-
-
-

### Instance type
- r7i.8xlarge (main)

## Architecture

<div align="center">

### Data Pipeline

</div>

```mermaid
flowchart LR
    subgraph Data_Source
        A[(Neo4j)]
    end

    subgraph Data_Processing
        B[Extract Data]
        C[Feature Engineering]
    end

    subgraph Modeling
        D[ML Model]
    end

    subgraph Output
        E[Predictions]
    end

    A --> B --> C --> D --> E
```

<div align="center">

### System Architecture

</div>


```mermaid
flowchart LR

U[User]

subgraph Oracle["<span style='color:#2c7be5'>Oracle Cloud (Frontend)</span>"]
    FE[Frontend Web App]
    SUBMIT["/submit Endpoint"]
end

subgraph AWS["<span style='color:#e67e22'>AWS EC2 Instance (Backend)</span>"]
    API[Backend API + ML Model]
end

subgraph Graph["<span style='color:#27ae60'>Neo4j Graph Database Server</span>"]
    DB[(Neo4j Database)]
end

R[Response Results]

U --> FE
FE --> SUBMIT
SUBMIT --> API
API --> DB
DB --> API
API --> R
R --> FE
FE --> U
```

## Base EC2 storage location for neo4j
/data/neo4j

# Credits and Acknowledgements
Full acknowledgements of this project to EBA and the neo4j ddatabase restoration.
- https://eba.b1aab.ai/
- https://eba.b1aab.ai/docs/bitcoin/etl/restore/ 
