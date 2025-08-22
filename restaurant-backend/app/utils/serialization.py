# app/utils/serialization.py
from __future__ import annotations
from typing import Any, Mapping
from decimal import Decimal
from fastapi.encoders import jsonable_encoder

# asyncpg Record is what databases/asyncpg returns for rows
try:
    from asyncpg import Record  # type: ignore
except Exception:  # pragma: no cover
    class Record:  # fallback so isinstance checks won't crash
        pass


def _normalize(obj: Any) -> Any:
    """Recursively convert DB/py types to JSON-safe ones."""
    # asyncpg Record -> dict
    if isinstance(obj, Record):
        return dict(obj)
    # Decimal -> float (or change to str if you prefer)
    if isinstance(obj, Decimal):
        return float(obj)
    # dict -> normalize values
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    # list/tuple/set -> normalize each element
    if isinstance(obj, (list, tuple, set)):
        return [_normalize(x) for x in obj]
    return obj


def encode_payload(payload: Mapping[str, Any]) -> dict:
    """
    Deep-normalize then run FastAPI's encoder.
    Returns a JSON-serializable dict you can pass to encryptResponse or JSONResponse.
    """
    normalized = _normalize(payload)
    return jsonable_encoder(normalized, custom_encoder={Decimal: float})
