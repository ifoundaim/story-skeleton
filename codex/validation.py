from __future__ import annotations

"""Placeholder validation helpers."""

from hashlib import sha256
from typing import Any


def validate_pose(data: dict[str, Any]) -> bool:
    return "pose" in data


def validate_schema(data: dict[str, Any]) -> bool:
    return "schema" in data


def asset_hash(data: bytes) -> str:
    return sha256(data).hexdigest()


VALIDATORS = {
    "pose": validate_pose,
    "schema": validate_schema,
}
