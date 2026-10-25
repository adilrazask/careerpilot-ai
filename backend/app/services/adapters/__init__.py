from app.services.adapters.base import JobSourceAdapter
from app.services.adapters.implementations import SourceManager, canonicalize_url, normalize_title
from app.services.adapters.apollo_adapter import ApolloContactAdapter

__all__ = ["JobSourceAdapter", "SourceManager", "canonicalize_url", "normalize_title", "ApolloContactAdapter"]
