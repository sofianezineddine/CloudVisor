"""Unit tests for the Avro serializer."""

import json
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAvroSerializerFallback:
    """Tests that run without fastavro or Schema Registry (JSON fallback path)."""

    def test_serialize_falls_back_to_json_when_not_available(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="")
        # _available is False by default
        payload = s.serialize("discovered", {"event_type": "resource.discovered", "name": "test"})
        # Should be valid JSON bytes
        decoded = json.loads(payload.decode("utf-8"))
        assert decoded["name"] == "test"

    def test_serialize_json_fallback_handles_non_serializable(self):
        from app.producers.avro_serializer import AvroSerializer
        from datetime import datetime
        s = AvroSerializer(schema_registry_url="")
        dt = datetime(2024, 1, 1)
        payload = s.serialize("discovered", {"ts": dt})
        decoded = json.loads(payload.decode("utf-8"))
        assert "2024" in decoded["ts"]

    def test_is_available_false_by_default(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="http://localhost:8081")
        assert s.is_available() is False

    @pytest.mark.asyncio
    async def test_initialize_returns_false_when_registry_unreachable(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="http://localhost:19999")
        result = await s.initialize()
        assert result is False
        assert s.is_available() is False

    @pytest.mark.asyncio
    async def test_initialize_returns_false_when_url_empty(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="")
        result = await s.initialize()
        assert result is False


class TestAvroSerializerWireFormat:
    """Tests for the Confluent wire format when Avro IS available."""

    def test_confluent_wire_format_magic_byte(self):
        """Avro payload must start with 0x00 (Confluent magic byte)."""
        try:
            import fastavro  # noqa: F401
        except ImportError:
            pytest.skip("fastavro not installed")

        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="http://localhost:8081")
        # Manually inject a fake schema + ID into the cache
        import fastavro.schema
        schema = fastavro.schema.parse_schema({
            "type": "record",
            "name": "Test",
            "namespace": "test",
            "fields": [
                {"name": "name", "type": "string"},
                {"name": "value", "type": "int", "default": 0},
            ],
        })
        s._schema_cache["test_topic"] = (schema, 42)
        s._available = True
        s._fastavro_available = True

        payload = s.serialize("test_topic", {"name": "hello", "value": 1})

        # First byte must be magic byte 0x00
        assert payload[0:1] == b"\x00"
        # Next 4 bytes are schema ID (big-endian)
        schema_id = struct.unpack(">I", payload[1:5])[0]
        assert schema_id == 42
        # Remaining bytes are Avro binary
        assert len(payload) > 5

    def test_sanitize_record_coerces_tags(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="")
        record = {"tags": {"key": 123, "other": True}}
        result = s._sanitize_record(record, None)
        assert result["tags"]["key"] == "123"
        assert result["tags"]["other"] == "True"

    def test_sanitize_record_coerces_numeric_fields(self):
        from app.producers.avro_serializer import AvroSerializer
        s = AvroSerializer(schema_registry_url="")
        record = {"discovered": "5", "errors": "0", "duration_seconds": "1.5"}
        result = s._sanitize_record(record, None)
        assert result["discovered"] == 5
        assert isinstance(result["discovered"], int)
        assert result["duration_seconds"] == 1.5
        assert isinstance(result["duration_seconds"], float)


class TestResourceEventProducerAvro:
    """Tests for the producer's Avro integration."""

    @pytest.mark.asyncio
    async def test_producer_uses_json_when_no_registry(self):
        from app.producers.resource_events import ResourceEventProducer
        producer = ResourceEventProducer(
            bootstrap_servers="localhost:9092",
            schema_registry_url="",
        )
        # Don't actually start Kafka — just verify serializer state
        assert producer._serializer is None

    @pytest.mark.asyncio
    async def test_serialize_resource_event_json_fallback(self):
        from app.producers.resource_events import ResourceEventProducer
        from cloudvisor_types.models import CloudResource, CloudProvider, Environment
        from datetime import datetime

        producer = ResourceEventProducer(
            bootstrap_servers="localhost:9092",
            schema_registry_url="",
        )
        # _serializer is None → JSON path
        resource = CloudResource(
            id="r-1",
            cloud_resource_id="arn:aws:ec2:us-east-1:123:instance/i-abc",
            provider=CloudProvider.AWS,
            account_id="123456789012",
            region="us-east-1",
            resource_type="aws::ec2::instance",
            name="my-instance",
            tags={"env": "prod"},
            raw={},
            organization_id="org-1",
            is_public=False,
            environment=Environment.PROD,
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )

        # Patch _send_event to capture the serialized payload
        captured = {}

        async def fake_send(topic_suffix, key, event):
            captured["payload"] = producer._serialize(topic_suffix, event)
            captured["event"] = event

        producer._send_event = fake_send
        await producer.emit_resource_discovered(resource, correlation_id="corr-1")

        assert "payload" in captured
        decoded = json.loads(captured["payload"].decode("utf-8"))
        assert decoded["event_type"] == "resource.discovered"
        assert decoded["organization_id"] == "org-1"
        assert decoded["correlation_id"] == "corr-1"
        assert decoded["tags"] == {"env": "prod"}
