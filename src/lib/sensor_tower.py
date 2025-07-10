"""Sensor Tower API client for market size analysis."""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import aiohttp
from pydantic import BaseModel


class SensorTowerAppData(BaseModel):
    """Sensor Tower app data model."""
    app_id: str
    humanized_name: str
    publisher_name: str
    bundle_id: str
    version: str
    rating: Optional[float]
    updated_date: str
    humanized_worldwide_last_month_revenue: Dict[str, Union[str, float]]
    humanized_worldwide_last_month_downloads: Dict[str, Union[str, int]]


@dataclass
class AppRevenueResult:
    """Result for app revenue analysis."""
    app_id: str
    app_name: str
    publisher: str
    last_month_revenue_usd: float
    last_month_revenue_string: str
    last_month_downloads: int
    last_month_downloads_string: str
    bundle_id: str
    version: str
    rating: Optional[float]
    last_updated: str
    source: str = "api"


class SensorTowerAPIClient:
    """Async Sensor Tower API client."""
    
    def __init__(self):
        self.base_url = "https://app.sensortower.com/api/ios/apps"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_app_revenue(self, app_ids: List[str]) -> Dict[str, Union[AppRevenueResult, Exception]]:
        """
        Fetch revenue data for multiple app IDs.
        
        Args:
            app_ids: List of iOS app IDs
            
        Returns:
            Dictionary mapping app_id to either AppRevenueResult or Exception
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        results = {}
        
        # Process apps in batches to avoid rate limiting
        batch_size = 20
        for i in range(0, len(app_ids), batch_size):
            batch = app_ids[i:i + batch_size]
            batch_results = await self._fetch_batch(batch)
            results.update(batch_results)
            
            # Rate limiting delay
            if i + batch_size < len(app_ids):
                await asyncio.sleep(1)
        
        return results
    
    
    async def _fetch_batch(self, app_ids: List[str]) -> Dict[str, Union[AppRevenueResult, Exception]]:
        """Fetch revenue data for a batch of apps."""
        app_ids_param = ",".join(app_ids)
        url = f"{self.base_url}?app_ids={app_ids_param}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        results = {}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 429:
                    error = ValueError("Rate limited by Sensor Tower API. Please try again later.")
                    for app_id in app_ids:
                        results[app_id] = error
                    return results
                
                if response.status != 200:
                    error = ValueError(f"API request failed with status {response.status}")
                    for app_id in app_ids:
                        results[app_id] = error
                    return results
                
                data = await response.json()
                
                # Parse the response
                apps = data.get("apps", [])
                
                # Map results by app_id
                for app in apps:
                    app_id_str = str(app.get("app_id", ""))
                    try:
                        result = self._parse_app_data(app)
                        results[app_id_str] = result
                    except Exception as e:
                        results[app_id_str] = e
                
                # Check for missing apps
                for app_id in app_ids:
                    if app_id not in results:
                        results[app_id] = ValueError(f"App ID {app_id} not found in Sensor Tower response")
                
                return results
                
        except aiohttp.ClientError as e:
            error = ValueError(f"Failed to fetch data from Sensor Tower: {e}")
            for app_id in app_ids:
                results[app_id] = error
            return results
    
    def _parse_app_data(self, data: dict) -> AppRevenueResult:
        """Parse Sensor Tower API response into AppRevenueResult."""
        try:
            app_id = str(data.get("app_id", ""))
            
            # Extract revenue data
            revenue_data = data.get("humanized_worldwide_last_month_revenue", {})
            revenue_usd = revenue_data.get("revenue", 0.0)
            revenue_string = revenue_data.get("string", "$0")
            
            # Extract downloads data
            downloads_data = data.get("humanized_worldwide_last_month_downloads", {})
            downloads = downloads_data.get("downloads", 0)
            downloads_string = downloads_data.get("string", "0")
            
            return AppRevenueResult(
                app_id=app_id,
                app_name=data.get("humanized_name", "Unknown"),
                publisher=data.get("publisher_name", "Unknown"),
                last_month_revenue_usd=float(revenue_usd),
                last_month_revenue_string=revenue_string,
                last_month_downloads=int(downloads),
                last_month_downloads_string=downloads_string,
                bundle_id=data.get("bundle_id", ""),
                version=data.get("version", ""),
                rating=data.get("rating"),
                last_updated=data.get("updated_date", ""),
                source="api"
            )
            
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Failed to parse app data: {e}")


class SimpleCache:
    """Simple in-memory cache for Sensor Tower data."""
    
    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, dict] = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def get(self, app_id: str) -> Optional[AppRevenueResult]:
        """Get cached data for an app."""
        if app_id not in self.cache:
            return None
        
        cached_item = self.cache[app_id]
        cached_time = datetime.fromisoformat(cached_item["timestamp"])
        
        # Check if cache is expired
        if datetime.now() - cached_time > self.ttl:
            del self.cache[app_id]
            return None
        
        # Return cached result
        data = cached_item["data"]
        data["source"] = "cache"
        return AppRevenueResult(**data)
    
    def set(self, app_id: str, result: AppRevenueResult):
        """Cache app revenue result."""
        self.cache[app_id] = {
            "timestamp": datetime.now().isoformat(),
            "data": {
                "app_id": result.app_id,
                "app_name": result.app_name,
                "publisher": result.publisher,
                "last_month_revenue_usd": result.last_month_revenue_usd,
                "last_month_revenue_string": result.last_month_revenue_string,
                "last_month_downloads": result.last_month_downloads,
                "last_month_downloads_string": result.last_month_downloads_string,
                "bundle_id": result.bundle_id,
                "version": result.version,
                "rating": result.rating,
                "last_updated": result.last_updated,
                "source": result.source
            }
        }
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "total_items": len(self.cache),
            "cache_keys": list(self.cache.keys())
        }


# Global cache instance
cache = SimpleCache()


async def get_apps_revenue(app_ids: List[str]) -> Dict[str, Union[AppRevenueResult, str]]:
    """
    Fetch revenue data for a list of app IDs with caching.
    
    Args:
        app_ids: List of iOS app IDs
        
    Returns:
        Dictionary mapping app_id to AppRevenueResult or error message
    """
    if not app_ids:
        raise ValueError("No app IDs provided")
    
    results = {}
    missing_app_ids = []
    
    # Check cache first
    for app_id in app_ids:
        cached_result = cache.get(app_id)
        if cached_result:
            results[app_id] = cached_result
        else:
            missing_app_ids.append(app_id)
    
    # Fetch missing data from API
    if missing_app_ids:
        try:
            async with SensorTowerAPIClient() as client:
                api_results = await client.fetch_app_revenue(missing_app_ids)
                
                for app_id, result in api_results.items():
                    if isinstance(result, Exception):
                        results[app_id] = str(result)
                    else:
                        # Cache successful result
                        cache.set(app_id, result)
                        results[app_id] = result
                        
        except Exception as e:
            # For missing apps, return error messages
            for app_id in missing_app_ids:
                if app_id not in results:
                    results[app_id] = f"Failed to fetch data: {e}"
    
    return results