from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class JobSourceAdapter(ABC):
    """Standardized interface for all job source portals and aggregators."""

    def __init__(self, name: str, category: str = "portal", rate_limit_per_minute: int = 10):
        self.name = name
        self.category = category
        self.rate_limit_per_minute = rate_limit_per_minute
        self.last_successful_request: Optional[datetime] = None
        self.last_error: str = ""
        self.is_connected: bool = False

    @abstractmethod
    def connect(self, config: Optional[Dict[str, Any]] = None) -> bool:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def search_jobs(self, query: str, location: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_job_details(self, job_id_or_url: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def verify_job_status(self, job_id_or_url: str) -> str:
        """Returns 'VERIFIED_OPEN', 'CLOSED', or 'UNCERTAIN'"""
        pass

    @abstractmethod
    def normalise_job(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_application_methods(self) -> List[str]:
        """Returns supported methods, e.g. ['email'], ['portal_redirect'], ['api']"""
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "is_connected": self.is_connected,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "last_successful_request": self.last_successful_request.isoformat() if self.last_successful_request else None,
            "last_error": self.last_error,
            "supported_application_methods": self.get_application_methods()
        }

    def close(self):
        self.is_connected = False
