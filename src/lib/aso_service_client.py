"""HTTP client for ASO Playwright Service."""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class KeywordMetrics:
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class ASOServiceClient:
    """HTTP client for ASO Playwright microservice."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def health_check(self) -> Dict:
        """Check service health."""
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_status(self) -> Dict:
        """Get service status."""
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_keywords(self, keywords: List[str]) -> Dict[str, KeywordMetrics]:
        """Analyze keywords using the service."""
        session = await self._get_session()
        
        payload = {"keywords": keywords}
        
        try:
            print(f"📤 Sending {len(keywords)} keywords to ASO service...")
            
            async with session.post(
                f"{self.base_url}/analyze-keywords",
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Convert response to KeywordMetrics objects
                    metrics = {}
                    for keyword, data in result.get('metrics', {}).items():
                        metrics[keyword] = KeywordMetrics(
                            difficulty=data['difficulty'],
                            traffic=data['traffic']
                        )
                    
                    print(f"✅ Received metrics for {len(metrics)} keywords")
                    print(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
                    
                    return metrics
                
                else:
                    error_text = await response.text()
                    print(f"❌ Service error: HTTP {response.status} - {error_text}")
                    return {}
                    
        except asyncio.TimeoutError:
            print("⏰ Service request timed out")
            return {}
        except Exception as e:
            print(f"❌ Service request failed: {e}")
            return {}


# Global client instance
_client = None


async def get_aso_service_client() -> ASOServiceClient:
    """Get global ASO service client."""
    global _client
    if _client is None:
        _client = ASOServiceClient()
    return _client


async def analyze_keywords_via_service(keywords: List[str]) -> Dict[str, KeywordMetrics]:
    """Analyze keywords using the ASO service."""
    client = await get_aso_service_client()
    
    # Check service health first
    health = await client.health_check()
    if health.get('status') != 'healthy':
        print(f"⚠️ Service health check failed: {health}")
        return {}
    
    # Analyze keywords
    return await client.analyze_keywords(keywords)