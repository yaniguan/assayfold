"""Connector registry. Any module here that defines CONNECTOR (a Connector subclass)
is registered under its source_id, so adding a source needs no edits to this file."""

import importlib
import pkgutil

_REGISTRY = {}


def _discover():
    if _REGISTRY:
        return
    for m in pkgutil.iter_modules(__path__):
        if m.name.startswith("_") or m.name == "base":
            continue
        mod = importlib.import_module(f"{__name__}.{m.name}")
        cls = getattr(mod, "CONNECTOR", None)
        if cls is not None:
            _REGISTRY[cls.source_id] = cls


def all_ids() -> list[str]:
    _discover()
    return sorted(_REGISTRY)


def get(source_id: str):
    """Return a connector instance for source_id."""
    _discover()
    if source_id not in _REGISTRY:
        raise KeyError(f"no connector {source_id!r}; known: {all_ids()}")
    return _REGISTRY[source_id]()
