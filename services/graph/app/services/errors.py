"""Graph service error types."""


class GraphError(Exception):
    """Base error for graph service."""
    pass


class NodeNotFoundError(GraphError):
    """Raised when a node is not found in the graph."""
    def __init__(self, node_id: str):
        super().__init__(f"Node not found: {node_id}")
        self.node_id = node_id


class RelationshipError(GraphError):
    """Raised when a relationship operation fails."""
    pass


class QueryError(GraphError):
    """Raised when a Cypher query fails."""
    pass


class IndexError(GraphError):
    """Raised when an Elasticsearch indexing operation fails."""
    pass
