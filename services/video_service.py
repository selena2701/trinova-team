import time
import requests
from typing import Dict, Any

from .base import BaseService, ServiceConfig

class VeoVideoService(BaseService):
    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    def start(self, prompt: str, negative_prompt: str = "blurry, low quality", aspect_ratio: str = "16:9", resolution: str = "720p", person_generation: str = "allow_all") -> str:
        url = f"{self.config.base_url}/gemini/v1beta/models/veo-3.0-generate-001:predictLongRunning"
        body = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "negativePrompt": negative_prompt,
                "aspectRatio": aspect_ratio,
                "resolution": resolution,
                "personGeneration": person_generation,
            },
        }
        resp = requests.post(url, headers=self.google_headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return data["name"]

    def status(self, operation_name: str) -> Dict[str, Any]:
        url = f"{self.config.base_url}/gemini/v1beta/{operation_name}"
        resp = requests.get(url, headers=self.google_headers)
        resp.raise_for_status()
        return resp.json()

    def wait_done(self, operation_name: str, timeout_sec: int = 900, interval_sec: int = 10) -> Dict[str, Any]:
        start = time.time()
        while time.time() - start < timeout_sec:
            s = self.status(operation_name)
            if s.get("done"):
                return s
            time.sleep(interval_sec)
        raise TimeoutError("Veo operation timed out")

    def download(self, status_response: Dict[str, Any], output_path: str) -> str:
        response = status_response.get("response", {})
        gen = response.get("generateVideoResponse", {})
        samples = gen.get("generatedSamples", [])
        if not samples:
            raise ValueError("No generated samples in status response")
        uri = samples[0].get("video", {}).get("uri")
        if not uri:
            raise ValueError("No video uri in status response")
        file_id = uri.split("/files/")[1].split(":download")[0]
        download_url = f"{self.config.base_url}/gemini/download/v1beta/files/{file_id}:download?alt=media"
        resp = requests.get(download_url, headers=self.google_headers)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path

