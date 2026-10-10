"""Shared document infrastructure adapters.

Purpose:
    Group concrete local document rendering, extraction, and artifact storage
    adapters that are reused across curated apps without leaking third-party
    library APIs into the application layer.

Relationships:
    Providers in ``skriptoteket.di.document_converter`` and
    ``skriptoteket.di.classroom_planner_class_lists`` expose these adapters
    through protocol seams for Document Converter and existing PDF-producing apps.
"""
