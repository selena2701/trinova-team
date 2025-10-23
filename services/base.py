"""
Base clients and utilities for AI Th ̣fc Chi ̣bn services
"""

import os
from typing import Dict, Any, Optional

class ServiceConfig:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")
        self.base_url = (base_url or os.getenv("AI_API_BASE") or "https://api.thucchien.ai").rstrip("/")
        if not self.api_key:
            raise ValueError("API key not configured. Set GEMINI_API_KEY or pass api_key explicitly.")

class BaseService:
    def __init__(self, config: ServiceConfig):
        self.config = config

    @property
    def bearer_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    @property
    def google_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.config.api_key,
        }


