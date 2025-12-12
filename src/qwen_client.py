"""Qwen API client using OAuth credentials."""

import json
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class QwenClient:
    """Client for Qwen API using OAuth credentials."""
    
    def __init__(self, creds_path: str = "/home/vyt/.qwen/oauth_creds.json"):
        self.creds_path = Path(creds_path)
        self._credentials: Optional[Dict[str, Any]] = None
        
    def _load_credentials(self) -> Dict[str, Any]:
        """Load OAuth credentials from file."""
        print(f"[DEBUG] Loading credentials from {self.creds_path}")
        
        if not self.creds_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.creds_path}")
        
        with open(self.creds_path) as f:
            creds = json.load(f)
        
        print(f"[DEBUG] Loaded credentials: {list(creds.keys())}")
        
        # Check if token is expired
        if "expiry_date" in creds:
            expiry = creds["expiry_date"]
            current_time = datetime.now().timestamp() * 1000
            print(f"[DEBUG] Token expiry: {expiry}, current: {current_time}")
            if isinstance(expiry, (int, float)) and expiry < current_time:
                raise ValueError("Access token has expired")
        
        return creds
    
    def _get_base_url(self, creds: Dict[str, Any]) -> str:
        """Get the correct base URL from credentials."""
        resource_url = creds.get("resource_url")
        if resource_url:
            base_url = resource_url if resource_url.startswith("http") else f"https://{resource_url}"
            return base_url if base_url.endswith("/v1") else f"{base_url}/v1"
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with OAuth token."""
        if not self._credentials:
            self._credentials = self._load_credentials()
        
        token = self._credentials.get("access_token")
        if not token:
            raise ValueError("No access token found in credentials")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def chat_completion(
        self,
        messages: list,
        model: str = "qwen3-coder-plus",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Make a chat completion request."""
        if not self._credentials:
            self._credentials = self._load_credentials()
        
        base_url = self._get_base_url(self._credentials)
        url = f"{base_url}/chat/completions"
        
        print(f"[DEBUG] Making chat completion request to {url}")
        print(f"[DEBUG] Model: {model}, Messages count: {len(messages)}")
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                print(f"[DEBUG] Sending request to {url}")
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0,
                )
                print(f"[DEBUG] Response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                print(f"[DEBUG] Response received successfully")
                return result
            except httpx.HTTPStatusError as e:
                print(f"[DEBUG] HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 401:
                    # Token might be expired, reload credentials
                    self._credentials = None
                    raise ValueError("Authentication failed - token may be expired")
                raise
            except Exception as e:
                print(f"[DEBUG] Request failed: {e}")
                raise
