"""Kafka consumers for the auth service.

Currently the auth service does not consume Kafka events, but this directory
is required by the standard service structure (spec §2.4).

Future consumers:
- user.deleted: cascade cleanup of sessions, API keys, audit logs
- org.plan_changed: update feature flags cache
"""
