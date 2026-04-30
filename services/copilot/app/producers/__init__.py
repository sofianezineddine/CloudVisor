"""Kafka producers for the Copilot service."""

from .audit_producer import AuditEventProducer

__all__ = ["AuditEventProducer"]
