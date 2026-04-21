"""Adapters towards the upstream repositories (`meta2`, `infom`, `in4n`).

These are intentionally minimal stubs. They define the contract the real
integrations should satisfy so that downstream code can depend on a stable
interface while the actual upstream code is wired in later.
"""

from .meta2_adapter import Meta2SignatureAdapter
from .infom_adapter import InfoMGraphAdapter
from .in4n_adapter import In4nSceneAdapter

__all__ = ["Meta2SignatureAdapter", "InfoMGraphAdapter", "In4nSceneAdapter"]
