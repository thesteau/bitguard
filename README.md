# BitGuard


## Teammates
-
-
-
-

### Instance type
- r7i.8xlarge (main)

## Architecture and Flow

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


## Base EC2 storage location for neo4j
/data/neo4j

# Credits and Acknowledgements
Full acknowledgements of this project to EBA and the neo4j ddatabase restoration.
- https://eba.b1aab.ai/
- https://eba.b1aab.ai/docs/bitcoin/etl/restore/ 
