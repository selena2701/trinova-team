import json
import base64
import requests
from typing import Dict, Any, List, Optional

from .base import BaseService, ServiceConfig

class ImageService(BaseService):
    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    def generate(self, prompt: str, model: str = "imagen-4", n: int = 1, size: Optional[str] = None, aspect_ratio: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url}/images/generations"
        body: Dict[str, Any] = {"prompt": prompt, "model": model, "n": n}
        if aspect_ratio:
            body["aspect_ratio"] = aspect_ratio
        elif size:
            body["size"] = size
        resp = requests.post(url, headers=self.bearer_headers, json=body)
        if resp.status_code == 200:
            return resp.json()
        # Log and try fallback OpenAI-style extra_body
        err_txt = resp.text
        try_body = {
            "model": model,
            "prompt": prompt,
            "n": str(n),
            "extra_body": {}
        }
        if aspect_ratio:
            try_body["extra_body"]["aspect_ratio"] = aspect_ratio
        elif size:
            try_body["extra_body"]["size"] = size
        resp2 = requests.post(url, headers=self.bearer_headers, json=try_body)
        if resp2.status_code == 200:
            return resp2.json()
        raise requests.HTTPError(f"Image generation failed: {resp.status_code} {err_txt} | fallback: {resp2.status_code} {resp2.text}")

    @staticmethod
    def save_b64_to_file(b64_json: str, output_path: str) -> str:
        image_bytes = base64.b64decode(b64_json)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path