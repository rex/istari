"""Istari backend — FastAPI modular monolith.

Layers (enforced by import-linter, see pyproject.toml):

    routes  →  services  →  adapters (db)  →  domain (pure)

`domain` never imports anything above it.
"""
