"""Application models for shared seating-export webhook bindings.

Purpose:
    Represent the single shared Sir Convert webhook subscription that multiple
    seating export jobs can reuse without coupling ownership to any one job
    record.

Relationships:
    - Persisted through `SeatingExportWebhookBindingRepositoryProtocol`.
    - Used by seating export-job handlers to serialize subscription creation
      behind one concurrency-safe binding record.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SeatingExportWebhookBinding(BaseModel):
    """Describe the shared Sir Convert webhook binding for seating exports."""

    model_config = ConfigDict(frozen=True)

    binding_key: str
    subscription_id: str | None = None
    callback_url: str | None = None
    secret: str | None = None
    created_at: datetime
    updated_at: datetime
