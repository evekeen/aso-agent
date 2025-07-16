"""ASO Store implementation following LangGraph Store interface patterns."""

import json
import aiosqlite
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from langgraph.store.base import BaseStore
from langgraph.store.base import Item


@dataclass
class ASOItem:
    """ASO-specific item for store."""
    key: str
    value: Dict[str, Any]
    namespace: Tuple[str, ...]
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None


class ASOSQLiteStore(BaseStore):
    """SQLite-based store following LangGraph Store interface patterns."""
    
    def __init__(self, db_path: str = "aso_store.db", ttl_days: int = 30):
        super().__init__()
        self.db_path = db_path
        self.ttl_days = ttl_days
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized (async lazy initialization)."""
        if not self._initialized:
            await self._init_db()
            self._initialized = True
    
    async def _init_db(self):
        """Initialize database tables following Store interface patterns."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Single items table following Store interface
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS aso_items (
                    namespace_path TEXT,
                    key TEXT,
                    value TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    expires_at TEXT,
                    PRIMARY KEY (namespace_path, key)
                )
            """)
            
            # Indexes for performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON aso_items(namespace_path)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON aso_items(expires_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON aso_items(created_at)")
            
            await conn.commit()
    
    def _namespace_to_path(self, namespace: Tuple[str, ...]) -> str:
        """Convert namespace tuple to string path."""
        return "/".join(namespace) if namespace else ""
    
    def _path_to_namespace(self, path: str) -> Tuple[str, ...]:
        """Convert string path to namespace tuple."""
        return tuple(path.split("/")) if path else ()
    
    def _calculate_expiry(self) -> str:
        """Calculate expiry timestamp."""
        expiry = datetime.now() + timedelta(days=self.ttl_days)
        return expiry.isoformat()
    
    async def aget(
        self,
        namespace: Tuple[str, ...],
        key: str
    ) -> Optional[Item]:
        """Get item by namespace and key."""
        await self._ensure_initialized()
        
        namespace_path = self._namespace_to_path(namespace)
        
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                SELECT * FROM aso_items 
                WHERE namespace_path = ? AND key = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (namespace_path, key, datetime.now().isoformat()))
            
            row = await cursor.fetchone()
            if row:
                return Item(
                    value=json.loads(row[2]),
                    key=row[1],
                    namespace=self._path_to_namespace(row[0]),
                    created_at=row[3],
                    updated_at=row[4]
                )
        return None
    
    async def aput(
        self,
        namespace: Tuple[str, ...],
        key: str,
        value: Dict[str, Any]
    ) -> None:
        """Put item in store."""
        await self._ensure_initialized()
        
        namespace_path = self._namespace_to_path(namespace)
        now = datetime.now().isoformat()
        expires_at = self._calculate_expiry()
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO aso_items 
                (namespace_path, key, value, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                namespace_path,
                key,
                json.dumps(value),
                now,
                now,
                expires_at
            ))
            await conn.commit()
    
    async def adelete(
        self,
        namespace: Tuple[str, ...],
        key: str
    ) -> None:
        """Delete item from store."""
        await self._ensure_initialized()
        
        namespace_path = self._namespace_to_path(namespace)
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                DELETE FROM aso_items 
                WHERE namespace_path = ? AND key = ?
            """, (namespace_path, key))
            await conn.commit()
    
    async def asearch(
        self,
        namespace_prefix: Tuple[str, ...],
        query: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Item]:
        """Search items by namespace prefix."""
        await self._ensure_initialized()
        
        namespace_path_prefix = self._namespace_to_path(namespace_prefix)
        
        # Build query
        sql = """
            SELECT * FROM aso_items 
            WHERE namespace_path LIKE ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        
        params = (
            f"{namespace_path_prefix}%",
            datetime.now().isoformat(),
            limit,
            offset
        )
        
        results = []
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            
            for row in rows:
                item = Item(
                    value=json.loads(row[2]),
                    key=row[1],
                    namespace=self._path_to_namespace(row[0]),
                    created_at=row[3],
                    updated_at=row[4]
                )
                results.append(item)
        
        return results
    
    async def alist_namespaces(
        self,
        prefix: Tuple[str, ...] = (),
        suffix: Tuple[str, ...] = (),
        max_depth: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tuple[str, ...]]:
        """List namespaces in store."""
        await self._ensure_initialized()
        
        prefix_path = self._namespace_to_path(prefix)
        
        sql = """
            SELECT DISTINCT namespace_path FROM aso_items 
            WHERE namespace_path LIKE ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY namespace_path
            LIMIT ? OFFSET ?
        """
        
        params = (
            f"{prefix_path}%",
            datetime.now().isoformat(),
            limit,
            offset
        )
        
        namespaces = []
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            
            for row in rows:
                namespace = self._path_to_namespace(row[0])
                if max_depth is None or len(namespace) <= max_depth:
                    namespaces.append(namespace)
        
        return namespaces
    
    async def clear_expired(self):
        """Remove expired items."""
        await self._ensure_initialized()
        
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                DELETE FROM aso_items 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            await conn.commit()
    
    async def get_stats(self) -> Dict[str, int]:
        """Get store statistics."""
        await self._ensure_initialized()
        
        async with aiosqlite.connect(self.db_path) as conn:
            stats = {}
            
            # Total items
            cursor = await conn.execute("SELECT COUNT(*) FROM aso_items")
            row = await cursor.fetchone()
            stats['total_items'] = row[0]
            
            # Active (non-expired) items
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM aso_items 
                WHERE expires_at IS NULL OR expires_at > ?
            """, (datetime.now().isoformat(),))
            row = await cursor.fetchone()
            stats['active_items'] = row[0]
            
            # Namespaces count
            cursor = await conn.execute("SELECT COUNT(DISTINCT namespace_path) FROM aso_items")
            row = await cursor.fetchone()
            stats['namespaces'] = row[0]
            
            return stats

    async def abatch(self, ops: List[Tuple[str, Tuple[str, ...], str, Any]]) -> List[Any]:
        """
        Execute multiple operations asynchronously in a single batch.
        
        Args:
            ops: List of operations, each tuple contains:
                - operation: "get" or "put" or "delete"
                - namespace: namespace tuple
                - key: item key
                - value: item value (for put operations, None for get/delete)
        
        Returns:
            List of results corresponding to each operation
        """
        await self._ensure_initialized()
        
        results = []
        for op_type, namespace, key, value in ops:
            if op_type == "get":
                result = await self.aget(namespace, key)
                results.append(result)
            elif op_type == "put":
                await self.aput(namespace, key, value)
                results.append(None)
            elif op_type == "delete":
                await self.adelete(namespace, key)
                results.append(None)
            else:
                raise ValueError(f"Unknown operation type: {op_type}")
        
        return results

    def batch(self, ops: List[Tuple[str, Tuple[str, ...], str, Any]]) -> List[Any]:
        """
        Execute multiple operations synchronously in a single batch.
        
        Args:
            ops: List of operations, each tuple contains:
                - operation: "get" or "put" or "delete"  
                - namespace: namespace tuple
                - key: item key
                - value: item value (for put operations, None for get/delete)
        
        Returns:
            List of results corresponding to each operation
        """
        import asyncio
        
        # Create event loop if none exists (for sync context)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async batch operation
        return loop.run_until_complete(self.abatch(ops))
    
    async def get_keyword_metrics(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Get cached keyword metrics (difficulty + traffic)."""
        item = await self.aget(ASONamespaces.keyword_metrics(), keyword.lower())
        return item.value if item else None
    
    async def set_keyword_metrics(self, keyword: str, difficulty: float, traffic: float) -> None:
        """Store keyword metrics (difficulty + traffic)."""
        await self.aput(
            ASONamespaces.keyword_metrics(),
            keyword.lower(),
            {
                "difficulty": difficulty,
                "traffic": traffic,
                "analyzed_at": datetime.now().isoformat()
            }
        )
    
    async def get_unanalyzed_keywords(self, keywords: List[str]) -> List[str]:
        """Filter out keywords that already have cached metrics."""
        unanalyzed = []
        for keyword in keywords:
            item = await self.aget(ASONamespaces.keyword_metrics(), keyword.lower())
            if not item:
                unanalyzed.append(keyword)
        return unanalyzed
    
    async def filter_weak_keywords(self, keywords: List[str]) -> tuple[List[str], List[str]]:
        """Filter out weak keywords (difficulty = 0.0) from keyword list.
        
        Returns:
            tuple: (valid_keywords, weak_keywords)
        """
        valid_keywords = []
        weak_keywords = []
        
        for keyword in keywords:
            metrics = await self.get_keyword_metrics(keyword)
            if metrics and metrics.get("difficulty", 0.0) == 0.0:
                weak_keywords.append(keyword)
            else:
                valid_keywords.append(keyword)
        
        return valid_keywords, weak_keywords


# ASO-specific namespace helpers
class ASONamespaces:
    """Namespace constants for ASO data types."""
    
    @staticmethod
    def keyword_difficulty() -> Tuple[str, ...]:
        """Namespace for keyword difficulty cache."""
        return ("aso", "keyword_difficulty")
    
    @staticmethod
    def keyword_traffic() -> Tuple[str, ...]:
        """Namespace for keyword traffic cache."""
        return ("aso", "keyword_traffic")
    
    @staticmethod
    def keyword_metrics() -> Tuple[str, ...]:
        """Namespace for combined keyword metrics (difficulty + traffic)."""
        return ("aso", "keyword_metrics")
    
    @staticmethod
    def app_revenue() -> Tuple[str, ...]:
        """Namespace for app revenue cache."""
        return ("aso", "app_revenue")
    
    @staticmethod
    def keyword_apps() -> Tuple[str, ...]:
        """Namespace for keyword-app associations."""
        return ("aso", "keyword_apps")
    
    @staticmethod
    def analysis_results() -> Tuple[str, ...]:
        """Namespace for analysis results."""
        return ("aso", "analysis_results")


# Global store instance
_store_instance = None

def get_aso_store(db_path: str = "aso_store.db", ttl_days: int = 30) -> ASOSQLiteStore:
    """Get or create ASO store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ASOSQLiteStore(db_path, ttl_days)
    return _store_instance