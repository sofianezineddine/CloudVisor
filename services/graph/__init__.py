"""CloudVisor Asset Graph Service.

Foundation 2 of the CloudVisor CNAPP platform - Central nervous system for
storing and querying cloud resources and their relationships.

## Overview

The Graph service is responsible for:
- Storing all cloud resources as nodes in Neo4j
- Managing relationships between resources
- Computing risk scores based on findings and exposure
- Syncing to Elasticsearch for full-text search
- Historical snapshotting for time-travel queries

## Architecture

Uses Neo4j for graph storage and Elasticsearch for full-text search.
All asset data flows through Kafka consumers from the Connector service.

## Supported Operations

- Create/update/delete asset nodes
- Query relationships (1-3 hops)
- Attack path analysis
- Full-text search via Elasticsearch
- Historical snapshots for compliance

## Configuration

Environment variables:
- GRAPH_NEO4J_URI - Neo4j connection URL
- GRAPH_NEO4J_USER - Neo4j username
- GRAPH_NEO4J_PASSWORD - Neo4j password
- GRAPH_ELASTICSEARCH_URL - Elasticsearch URL

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /internal/assets | List assets (filtered, paginated) |
| GET | /internal/assets/{id} | Get single asset |
| GET | /internal/assets/{id}/related | Get related assets |
| GET | /internal/assets/{id}/history | Get historical snapshots |
| GET | /internal/assets/{id}/attack-paths | Compute attack paths |
| GET | /internal/assets/search | Full-text search |
| POST | /internal/assets/query | Execute Cypher query |
| GET | /internal/graph/stats | Get graph statistics |
"""

__version__ = "1.0.0"


def get_app():
    """Lazy import to avoid triggering app startup at import time."""
    from .main import app
    return app


__all__ = ["get_app"]
