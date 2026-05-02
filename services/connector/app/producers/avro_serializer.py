"""Confluent-compatible Avro serializer with Schema Registry integration.

Implements the Confluent wire format:
  [0x00] [4-byte schema ID big-endian] [Avro binary payload]

On first use each schema is registered (or fetched if already registered)
from the Confluent Schema Registry.  Schema IDs are cached in-process so
every subsequent serialization is a pure in-memory operation.

Falls back to plain JSON serialization when Schema Registry is unavailable
so the service keeps running in development environments without a registry.
"""

import io
import json
import logging
import struct
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Confluent magic byte that prefixes every Avro-serialized message
_MAGIC_BYTE = b"\x00"

# Path to the .avsc schema files shipped with the monorepo
_SCHEMA_DIR = Path(__file__).parent.parent.parent / "packages" / "kafka-schemas" / "connector"


class SchemaRegistryError(Exception):
    """Raised when Schema Registry communication fails."""


class AvroSerializer:
    """
    Serializes Python dicts to Confluent Avro wire format.

    Usage:
        serializer = AvroSerializer(schema_registry_url="http://localhost:8081")
        await serializer.initialize()
        payload = serializer.serialize("resource.discovered", event_dict)
    """

    # Maps topic-suffix → .avsc filename
    TOPIC_SCHEMA_MAP: dict[str, str] = {
        "discovered":    "resource_discovered.avsc",
        "updated":       "resource_updated.avsc",
        "deleted":       "resource_deleted.avsc",
        "sync_started":  "connector_sync.avsc",
        "sync_finished": "connector_sync.avsc",
        "health_changed":"connector_health.avsc",
    }

    def __init__(self, schema_registry_url: str):
        self._registry_url = schema_registry_url.rstrip("/")
        # topic_suffix → (parsed_schema, schema_id)
        self._schema_cache: dict[str, tuple[Any, int]] = {}
        self._available = False
        self._fastavro_available = False

    async def initialize(self) -> bool:
        """
        Connect to Schema Registry and register all schemas.
        Returns True if Avro serialization is available, False if falling back to JSON.
        """
        try:
            import fastavro  # noqa: F401
            self._fastavro_available = True
        except ImportError:
            logger.warning(
                "fastavro not installed — Avro serialization disabled. "
                "Install with: pip install fastavro"
            )
            return False

        if not self._registry_url:
            logger.warning("KAFKA_SCHEMA_REGISTRY_URL not set — Avro serialization disabled")
            return False

        # Test connectivity
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._registry_url}/subjects")
                if resp.status_code not in (200, 404):
                    raise SchemaRegistryError(f"Unexpected status {resp.status_code}")
        except Exception as e:
            logger.warning(
                f"Schema Registry unreachable at {self._registry_url}: {e}. "
                "Falling back to JSON serialization."
            )
            return False

        # Register all schemas
        all_ok = True
        for topic_suffix, avsc_file in self.TOPIC_SCHEMA_MAP.items():
            if topic_suffix in self._schema_cache:
                continue  # already registered (shared schema)
            try:
                schema_id = await self._register_schema(avsc_file)
                parsed = self._load_schema(avsc_file)
                self._schema_cache[topic_suffix] = (parsed, schema_id)
                logger.info(
                    f"Schema registered: {avsc_file} → id={schema_id} "
                    f"(topic_suffix={topic_suffix})"
                )
            except Exception as e:
                logger.error(f"Failed to register schema {avsc_file}: {e}")
                all_ok = False

        self._available = all_ok
        if self._available:
            logger.info("Avro serialization active — all schemas registered")
        else:
            logger.warning("Some schemas failed to register — falling back to JSON")
        return self._available

    def serialize(self, topic_suffix: str, record: dict[str, Any]) -> bytes:
        """
        Serialize a record to Confluent Avro wire format.
        Falls back to UTF-8 JSON if Avro is not available.
        """
        if not self._available or topic_suffix not in self._schema_cache:
            return json.dumps(record, default=str).encode("utf-8")

        import fastavro

        parsed_schema, schema_id = self._schema_cache[topic_suffix]

        # Sanitize: Avro maps require string values; convert non-strings
        clean_record = self._sanitize_record(record, parsed_schema)

        buf = io.BytesIO()
        # Confluent wire format header: magic byte + 4-byte schema ID
        buf.write(_MAGIC_BYTE)
        buf.write(struct.pack(">I", schema_id))
        # Avro binary payload
        fastavro.schemaless_writer(buf, parsed_schema, clean_record)
        return buf.getvalue()

    def is_available(self) -> bool:
        return self._available

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_schema(self, avsc_file: str) -> Any:
        """Load and parse an Avro schema from the kafka-schemas package."""
        import fastavro.schema
        schema_path = _SCHEMA_DIR / avsc_file
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        with open(schema_path, encoding="utf-8") as f:
            return fastavro.schema.parse_schema(json.load(f))

    async def _register_schema(self, avsc_file: str) -> int:
        """
        Register a schema with the Confluent Schema Registry.
        Returns the schema ID (existing or newly assigned).
        """
        import httpx

        schema_path = _SCHEMA_DIR / avsc_file
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, encoding="utf-8") as f:
            schema_str = f.read()

        # Subject name convention: <topic>-value
        # We use the avsc filename stem as the subject name
        subject = avsc_file.replace(".avsc", "")

        payload = {"schema": schema_str, "schemaType": "AVRO"}

        async with httpx.AsyncClient(timeout=10) as client:
            # Try to register (idempotent — returns existing ID if schema unchanged)
            resp = await client.post(
                f"{self._registry_url}/subjects/{subject}/versions",
                json=payload,
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            )
            if resp.status_code in (200, 201):
                return resp.json()["id"]

            # If conflict (schema already exists with different ID), fetch existing
            if resp.status_code == 409:
                resp2 = await client.post(
                    f"{self._registry_url}/subjects/{subject}",
                    json=payload,
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                )
                if resp2.status_code == 200:
                    return resp2.json()["id"]

            raise SchemaRegistryError(
                f"Schema registration failed for {subject}: "
                f"HTTP {resp.status_code} — {resp.text[:200]}"
            )

    def _sanitize_record(self, record: dict[str, Any], schema: Any) -> dict[str, Any]:
        """
        Ensure the record matches the Avro schema constraints:
        - Map fields must have string values
        - Null union fields must be None or the correct type
        - Numeric fields must be int/float not str
        """
        result = dict(record)

        # Coerce tags map: values must be strings
        if "tags" in result and isinstance(result["tags"], dict):
            result["tags"] = {
                str(k): str(v) for k, v in result["tags"].items()
            }

        # Coerce raw map if present (resource events carry raw data)
        if "raw" in result and isinstance(result["raw"], dict):
            result["raw"] = {
                str(k): json.dumps(v, default=str) if not isinstance(v, str) else v
                for k, v in result["raw"].items()
            }

        # Ensure numeric fields are correct types
        for int_field in ("discovered", "updated", "deleted", "errors", "resource_count"):
            if int_field in result:
                result[int_field] = int(result[int_field])

        if "duration_seconds" in result:
            result["duration_seconds"] = float(result["duration_seconds"])

        return result
