"""Cache store for ASO analysis data using SQLite."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class CachedKeywordDifficulty:
    keyword: str
    difficulty_score: float
    title_matches_score: float
    competitors: int
    competitors_score: float
    installs_score: float
    rating_score: float
    age_score: float
    analyzed_at: str
    expires_at: str


@dataclass
class CachedRevenue:
    app_id: str
    revenue_usd: float
    revenue_string: str
    downloads: int
    downloads_string: str
    app_name: str
    publisher: str
    analyzed_at: str
    expires_at: str


class ASOCacheStore:
    """SQLite-based cache for ASO analysis data."""
    
    def __init__(self, db_path: str = "aso_cache.db", ttl_days: int = 30):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Keyword difficulty cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_difficulty_cache (
                    keyword TEXT PRIMARY KEY,
                    difficulty_score REAL,
                    title_matches_score REAL,
                    competitors INTEGER,
                    competitors_score REAL,
                    installs_score REAL,
                    rating_score REAL,
                    age_score REAL,
                    analyzed_at TEXT,
                    expires_at TEXT
                )
            """)
            
            # Revenue cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revenue_cache (
                    app_id TEXT PRIMARY KEY,
                    revenue_usd REAL,
                    revenue_string TEXT,
                    downloads INTEGER,
                    downloads_string TEXT,
                    app_name TEXT,
                    publisher TEXT,
                    analyzed_at TEXT,
                    expires_at TEXT
                )
            """)
            
            # Keyword-app associations table (for market size calculations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_app_associations (
                    keyword TEXT,
                    app_id TEXT,
                    position INTEGER,
                    analyzed_at TEXT,
                    expires_at TEXT,
                    PRIMARY KEY (keyword, app_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyword_expires ON keyword_difficulty_cache(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_revenue_expires ON revenue_cache(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_associations_keyword ON keyword_app_associations(keyword)")
            
            conn.commit()
    
    def _calculate_expiry(self) -> str:
        """Calculate expiry timestamp."""
        expiry = datetime.now() + timedelta(days=self.ttl_days)
        return expiry.isoformat()
    
    def get_keyword_difficulty(self, keyword: str) -> Optional[CachedKeywordDifficulty]:
        """Get cached keyword difficulty if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM keyword_difficulty_cache 
                WHERE keyword = ? AND expires_at > ?
            """, (keyword.lower(), datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                return CachedKeywordDifficulty(
                    keyword=row[0],
                    difficulty_score=row[1],
                    title_matches_score=row[2],
                    competitors=row[3],
                    competitors_score=row[4],
                    installs_score=row[5],
                    rating_score=row[6],
                    age_score=row[7],
                    analyzed_at=row[8],
                    expires_at=row[9]
                )
        return None
    
    def set_keyword_difficulty(self, keyword: str, difficulty_result: Dict[str, Any]):
        """Cache keyword difficulty analysis result."""
        now = datetime.now().isoformat()
        expires_at = self._calculate_expiry()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO keyword_difficulty_cache 
                (keyword, difficulty_score, title_matches_score, competitors, 
                 competitors_score, installs_score, rating_score, age_score, 
                 analyzed_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                keyword.lower(),
                difficulty_result.get('score', 0),
                difficulty_result.get('title_matches', {}).get('score', 0),
                difficulty_result.get('competitors', 0),
                difficulty_result.get('competitors_score', 0),
                difficulty_result.get('installs_score', 0),
                difficulty_result.get('rating_score', 0),
                difficulty_result.get('age_score', 0),
                now,
                expires_at
            ))
            conn.commit()
    
    def get_app_revenue(self, app_id: str) -> Optional[CachedRevenue]:
        """Get cached app revenue if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM revenue_cache 
                WHERE app_id = ? AND expires_at > ?
            """, (app_id, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                return CachedRevenue(
                    app_id=row[0],
                    revenue_usd=row[1],
                    revenue_string=row[2],
                    downloads=row[3],
                    downloads_string=row[4],
                    app_name=row[5],
                    publisher=row[6],
                    analyzed_at=row[7],
                    expires_at=row[8]
                )
        return None
    
    def set_app_revenue(self, app_id: str, revenue_result: Any):
        """Cache app revenue analysis result."""
        now = datetime.now().isoformat()
        expires_at = self._calculate_expiry()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO revenue_cache 
                (app_id, revenue_usd, revenue_string, downloads, downloads_string,
                 app_name, publisher, analyzed_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_id,
                revenue_result.last_month_revenue_usd,
                revenue_result.last_month_revenue_string,
                revenue_result.last_month_downloads,
                revenue_result.last_month_downloads_string,
                revenue_result.app_name,
                revenue_result.publisher,
                now,
                expires_at
            ))
            conn.commit()
    
    def set_keyword_apps(self, keyword: str, app_ids: List[str]):
        """Cache keyword-app associations for market size calculations."""
        now = datetime.now().isoformat()
        expires_at = self._calculate_expiry()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Remove old associations
            cursor.execute("DELETE FROM keyword_app_associations WHERE keyword = ?", 
                         (keyword.lower(),))
            
            # Insert new associations
            for position, app_id in enumerate(app_ids):
                cursor.execute("""
                    INSERT INTO keyword_app_associations 
                    (keyword, app_id, position, analyzed_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (keyword.lower(), app_id, position, now, expires_at))
            
            conn.commit()
    
    def get_keyword_apps(self, keyword: str) -> List[str]:
        """Get cached app IDs for a keyword if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT app_id FROM keyword_app_associations 
                WHERE keyword = ? AND expires_at > ?
                ORDER BY position
            """, (keyword.lower(), datetime.now().isoformat()))
            
            return [row[0] for row in cursor.fetchall()]
    
    def get_bulk_revenues(self, app_ids: List[str]) -> Dict[str, CachedRevenue]:
        """Get multiple app revenues in one query."""
        if not app_ids:
            return {}
        
        placeholders = ','.join('?' * len(app_ids))
        query = f"""
            SELECT * FROM revenue_cache 
            WHERE app_id IN ({placeholders}) AND expires_at > ?
        """
        
        results = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, app_ids + [datetime.now().isoformat()])
            
            for row in cursor.fetchall():
                revenue = CachedRevenue(
                    app_id=row[0],
                    revenue_usd=row[1],
                    revenue_string=row[2],
                    downloads=row[3],
                    downloads_string=row[4],
                    app_name=row[5],
                    publisher=row[6],
                    analyzed_at=row[7],
                    expires_at=row[8]
                )
                results[row[0]] = revenue
        
        return results
    
    def clear_expired(self):
        """Remove expired cache entries."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM keyword_difficulty_cache WHERE expires_at < ?", (now,))
            cursor.execute("DELETE FROM revenue_cache WHERE expires_at < ?", (now,))
            cursor.execute("DELETE FROM keyword_app_associations WHERE expires_at < ?", (now,))
            conn.commit()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total cached keywords
            cursor.execute("SELECT COUNT(*) FROM keyword_difficulty_cache")
            stats['total_keywords'] = cursor.fetchone()[0]
            
            # Active (non-expired) keywords
            cursor.execute("""
                SELECT COUNT(*) FROM keyword_difficulty_cache 
                WHERE expires_at > ?
            """, (datetime.now().isoformat(),))
            stats['active_keywords'] = cursor.fetchone()[0]
            
            # Total cached revenues
            cursor.execute("SELECT COUNT(*) FROM revenue_cache")
            stats['total_revenues'] = cursor.fetchone()[0]
            
            # Active revenues
            cursor.execute("""
                SELECT COUNT(*) FROM revenue_cache 
                WHERE expires_at > ?
            """, (datetime.now().isoformat(),))
            stats['active_revenues'] = cursor.fetchone()[0]
            
            return stats


# Global cache instance
_cache_instance = None

def get_cache_store(db_path: str = "aso_cache.db", ttl_days: int = 30) -> ASOCacheStore:
    """Get or create cache store instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ASOCacheStore(db_path, ttl_days)
    return _cache_instance