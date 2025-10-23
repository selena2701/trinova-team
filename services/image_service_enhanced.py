"""
Enhanced Image Service with additional features.

This module provides advanced image generation capabilities including:
- Chat-based image generation via /chat/completions
- Anti-caching mechanisms
- URL response handling
- Multiple generation methods

Use this service when you need:
- More creative/prompted image generation
- Avoiding cached responses
- Different model capabilities
- Multi-modal conversations with images
"""

import json
import base64
import requests
import random
from typing import Dict, Any, List, Optional

from .base import BaseService, ServiceConfig

class EnhancedImageService(BaseService):
    """
    Enhanced Image Service with advanced features.
    
    Provides both standard and chat-based image generation methods.
    """
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    def generate_via_chat(self, prompt: str, model: str = "gemini-2.5-flash-image-preview") -> bytes:
        """
        Generate image using chat completions endpoint.
        
        This method uses the /chat/completions endpoint with multimodal models
        that can generate images directly in conversation.
        
        Args:
            prompt: Text description of the image to generate
            model: Model to use (default: gemini-2.5-flash-image-preview)
            
        Returns:
            Image data as bytes
            
        When to use:
        - When you need more creative/prompted image generation
        - When working with multimodal models
        - When you want conversation-style image generation
        """
        url = f"{self.config.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=self.bearer_headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract base64 image data from response
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices in chat image response")
                
            message = choices[0].get("message", {})
            images = message.get("images", [])
            if not images:
                raise ValueError("No images in chat response")
                
            image_url = images[0].get("image_url", {}).get("url")
            if not image_url:
                raise ValueError("No image URL in chat response")
            
            # Handle data URL format (data:image/png;base64,...)
            if ',' in image_url:
                header, encoded = image_url.split(',', 1)
            else:
                encoded = image_url
            
            # Decode base64 image data
            image_bytes = base64.b64decode(encoded)
            return image_bytes
            
        except requests.exceptions.RequestException as e:
            raise requests.HTTPError(f"Chat image generation failed: {e}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Chat image response parsing failed: {e}")

    def add_anti_cache_suffix(self, prompt: str) -> str:
        """
        Add random suffix to prompt to avoid caching issues.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Prompt with random anti-cache suffix
            
        When to use:
        - When you're getting cached/repeated images
        - When you need slight variations in similar prompts
        - When testing image generation with similar prompts
        """
        random_suffix = str(random.randint(1, 10000))
        return f"{prompt}, {random_suffix}"

    def generate_with_anti_cache(self, prompt: str, model: str = "imagen-4", **kwargs) -> Dict[str, Any]:
        """
        Generate image with anti-caching enabled.
        
        Args:
            prompt: Text description of the image
            model: Model to use
            **kwargs: Additional parameters for image generation
            
        Returns:
            Image generation response
            
        When to use:
        - When you need to avoid cached responses
        - When generating multiple similar images
        - When testing with repeated prompts
        """
        enhanced_prompt = self.add_anti_cache_suffix(prompt)
        return self.generate(enhanced_prompt, model=model, **kwargs)

    def generate(self, prompt: str, model: str = "imagen-4", n: int = 1, 
                size: Optional[str] = None, aspect_ratio: Optional[str] = None) -> Dict[str, Any]:
        """
        Standard image generation (inherited from base ImageService).
        
        This method provides the standard /images/generations endpoint functionality.
        
        When to use:
        - For standard image generation
        - When you need specific size/aspect ratio control
        - When working with dedicated image models
        """
        url = f"{self.config.base_url}/images/generations"
        body: Dict[str, Any] = {"prompt": prompt, "model": model, "n": n}
        if aspect_ratio:
            body["aspect_ratio"] = aspect_ratio
        elif size:
            body["size"] = size
            
        try:
            resp = requests.post(url, headers=self.bearer_headers, json=body)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            # Try fallback OpenAI-style extra_body
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
            resp2.raise_for_status()
            return resp2.json()

    def generate_and_save_chat(self, prompt: str, output_path: str, 
                              model: str = "gemini-2.5-flash-image-preview") -> str:
        """
        Generate image via chat and save to file.
        
        Args:
            prompt: Text description of the image
            output_path: Path to save the image
            model: Model to use
            
        Returns:
            Path to saved image file
            
        When to use:
        - When you want chat-based generation with direct file saving
        - When working with multimodal models
        - When you need creative/conversational image generation
        """
        image_bytes = self.generate_via_chat(prompt, model)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path

    def generate_and_save_standard(self, prompt: str, output_path: str, 
                                  model: str = "imagen-4", **kwargs) -> str:
        """
        Generate image via standard endpoint and save to file.
        
        Args:
            prompt: Text description of the image
            output_path: Path to save the image
            model: Model to use
            **kwargs: Additional parameters
            
        Returns:
            Path to saved image file
            
        When to use:
        - For standard image generation with file saving
        - When you need specific size/aspect ratio control
        - When working with dedicated image models
        """
        response = self.generate(prompt, model=model, **kwargs)
        
        if response.get("data"):
            b64_data = response["data"][0].get("b64_json")
            if b64_data:
                image_bytes = base64.b64decode(b64_data)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                return output_path
            else:
                raise ValueError("No b64_json in response")
        else:
            raise ValueError("No data in response")

    @staticmethod
    def save_b64_to_file(b64_json: str, output_path: str) -> str:
        """Save base64 encoded image to file."""
        image_bytes = base64.b64decode(b64_json)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return output_path


