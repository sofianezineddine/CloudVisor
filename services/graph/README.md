# CloudVisor Graph Service

Unified Asset Graph & Inventory Service - Foundation 2 of the CloudVisor CNAPP platform.

## Overview

The Graph service is the central nervous system of CloudVisor. It stores
every cloud resource discovered by the Connector as a node in Neo4j,
along with the relationships between those resources.

## Key Features

- **Graph Storage**: Neo4j for storing resources and relationships
- **Full-text Search**: Elasticsearch sync for search
- **Risk Scoring**: Automated risk score computation
- **Attack Path Analysis**: Find dangerous paths in the graph
- **Historical Snapshots**: Time-travel queries for compliance

## Supported Queries

```cypher
-- All internet-exposed resources with open findings
MATCH (r)-[:ALLOWS_INBOUND_FROM]->(c:CIDR {value: "0.0.0.0/0"})
WHERE r.open_findings_count > 0
RETURN r ORDER BY r.risk_score DESC LIMIT 100

-- Full attack path: internet → sensitive database
MATCH path = (i:InternetGateway)-[*1..6]->(db:RDSInstance)
WHERE db.contains_pii = true
RETURN path, length(path) ORDER BY length(path) ASC LIMIT 10

-- Over-privileged IAM roles
MATCH (role:IAMRole)-[:HAS_ACCESS_TO]->(res)
WHERE role.unused_permissions_count > 20 AND res.environment = 'prod'
RETURN role, collect(res) AS prod_resources
```

## Configuration

```bash
GRAPH_NEO4J_URI=bolt://neo4j:7687
GRAPH_NEO4J_USER=neo4j
GRAPH_NEO4J_PASSWORD=password
GRAPH_ELASTICSEARCH_URL=http://elasticsearch:9200
```

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m graph.main
```

## Docker

```bash
docker build -t cloudvisor-graph .
docker run -p 8001:8001 cloudvisor-graph
```