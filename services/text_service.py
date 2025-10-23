import json
import requests
from typing import List, Dict, Any, Optional

from .base import BaseService, ServiceConfig

class TextService(BaseService):
    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    def chat(self, messages: List[Dict[str, str]], model: str = "gemini-2.5-flash", temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        url = f"{self.config.base_url}/chat/completions"
        body: Dict[str, Any] = {"model": model, "messages": messages}
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        resp = requests.post(url, headers=self.bearer_headers, data=json.dumps(body))
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


