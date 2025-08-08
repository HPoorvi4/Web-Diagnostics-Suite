"""
Cache service for web diagnostics suite.
Provides multi-level caching with TTL, LRU eviction, and persistent storage options.
"""

import json
import pickle
import hashlib
import time
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
import sqlite3
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    DISK = "disk"
    SQLITE = "sqlite"
    HYBRID = "hybrid"


@dataclass
class CacheConfig:
    """Configuration for cache service."""
    backend: CacheBackend = CacheBackend.MEMORY
    max_size: int = 1000  # Maximum number of items
    default_ttl: int = 3600  # Default TTL in seconds
    cleanup_interval: int = 300  # Cleanup interval in seconds
    disk_cache_dir: str = "cache"
    sqlite_db_path: str = "cache.db"
    compression: bool = True
    serializer: str = "json"  # "json" or "pickle"


@dataclass
class CacheItem:
    """Cache item with metadata."""
    key: str
    value: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = 0
    size: int = 0

    def __post_init__(self):
        if self.last_accessed == 0:
            self.last_accessed = self.created_at
            
    def is_expired(self) -> bool:
        """Check if cache item is expired."""
        if self.ttl <= 0:  # Never expires
            return False
        return time.time() - self.created_at > self.ttl
        
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class CacheBackendInterface(ABC):
    """Abstract interface for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheItem]:
        """Get item from cache."""
        pass
        
    @abstractmethod
    def set(self, key: str, item: CacheItem) -> bool:
        """Set item in cache."""
        pass
        
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        pass
        
    @abstractmethod
    def clear(self):
        """Clear all items from cache."""
        pass
        
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all cache keys."""
        pass
        
    @abstractmethod
    def size(self) -> int:
        """Get number of items in cache."""
        pass


class MemoryCache(CacheBackendInterface):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheItem] = OrderedDict()
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[CacheItem]:
        with self._lock:
            if key not in self._cache:
                return None
                
            item = self._cache[key]
            if item.is_expired():
                del self._cache[key]
                return None
                
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            item.update_access()
            return item
            
    def set(self, key: str, item: CacheItem) -> bool:
        with self._lock:
            # Remove if exists to update position
            if key in self._cache:
                del self._cache[key]
                
            # Add new item
            self._cache[key] = item
            
            # Evict if over size limit
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                
            return True
            
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
            
    def clear(self):
        with self._lock:
            self._cache.clear()
            
    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())
            
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class DiskCache(CacheBackendInterface):
    """Disk-based cache backend."""
    
    def __init__(self, cache_dir: str = "cache", compression: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.compression = compression
        self._lock = threading.RLock()
        
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
        
    def get(self, key: str) -> Optional[CacheItem]:
        with self._lock:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None
                
            try:
                with open(file_path, 'rb') as f:
                    if self.compression:
                        import gzip
                        data = gzip.decompress(f.read())
                    else:
                        data = f.read()
                        
                item = pickle.loads(data)
                
                if item.is_expired():
                    file_path.unlink(missing_ok=True)
                    return None
                    
                item.update_access()
                # Save updated access info
                self.set(key, item)
                return item
                
            except Exception as e:
                logger.error(f"Error reading cache file {file_path}: {e}")
                file_path.unlink(missing_ok=True)
                return None
                
    def set(self, key: str, item: CacheItem) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)
            try:
                data = pickle.dumps(item)
                if self.compression:
                    import gzip
                    data = gzip.compress(data)
                    
                with open(file_path, 'wb') as f:
                    f.write(data)
                    
                return True
            except Exception as e:
                logger.error(f"Error writing cache file {file_path}: {e}")
                return False
                
    def delete(self, key: str) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
            
    def clear(self):
        with self._lock:
            for file_path in self.cache_dir.glob("*.cache"):
                file_path.unlink()
                
    def keys(self) -> List[str]:
        # Note: This is expensive for disk cache
        # In practice, you'd maintain an index
        return []
        
    def size(self) -> int:
        with self._lock:
            return len(list(self.cache_dir.glob("*.cache")))


class SQLiteCache(CacheBackendInterface):
    """SQLite-based cache backend."""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at REAL,
                    ttl INTEGER,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    size INTEGER DEFAULT 0
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)')
            
    def get(self, key: str) -> Optional[CacheItem]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT value, created_at, ttl, access_count, last_accessed, size FROM cache WHERE key = ?',
                    (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                    
                value_blob, created_at, ttl, access_count, last_accessed, size = row
                value = pickle.loads(value_blob)
                
                item = CacheItem(
                    key=key,
                    value=value,
                    created_at=created_at,
                    ttl=ttl,
                    access_count=access_count,
                    last_accessed=last_accessed,
                    size=size
                )
                
                if item.is_expired():
                    conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                    return None
                    
                # Update access info
                item.update_access()
                conn.execute('''
                    UPDATE cache 
                    SET access_count = ?, last_accessed = ? 
                    WHERE key = ?
                ''', (item.access_count, item.last_accessed, key))
                
                return item
                
    def set(self, key: str, item: CacheItem) -> bool:
        with self._lock:
            try:
                value_blob = pickle.dumps(item.value)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO cache 
                        (key, value, created_at, ttl, access_count, last_accessed, size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        key, value_blob, item.created_at, item.ttl,
                        item.access_count, item.last_accessed, len(value_blob)
                    ))
                return True
            except Exception as e:
                logger.error(f"Error setting cache item {key}: {e}")
                return False
                
    def delete(self, key: str) -> bool:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                return cursor.rowcount > 0
                
    def clear(self):
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM cache')
                
    def keys(self) -> List[str]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT key FROM cache')
                return [row[0] for row in cursor.fetchall()]
                
    def size(self) -> int:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM cache')
                return cursor.fetchone()[0]


class CacheService:
    """Main cache service with multiple backends and advanced features."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache service.
        
        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self._backend = self._create_backend()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
    def _create_backend(self) -> CacheBackendInterface:
        """Create cache backend based on configuration."""
        if self.config.backend == CacheBackend.MEMORY:
            return MemoryCache(self.config.max_size)
        elif self.config.backend == CacheBackend.DISK:
            return DiskCache(self.config.disk_cache_dir, self.config.compression)
        elif self.config.backend == CacheBackend.SQLITE:
            return SQLiteCache(self.config.sqlite_db_path)
        elif self.config.backend == CacheBackend.HYBRID:
            # Hybrid implementation would combine memory + disk
            return MemoryCache(self.config.max_size)
        else:
            raise ValueError(f"Unknown cache backend: {self.config.backend}")
            
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            item = self._backend.get(key)
            if item:
                self._stats['hits'] += 1
                return item.value
            else:
                self._stats['misses'] += 1
                return None
                
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None uses default)
            
        Returns:
            True if successful
        """
        with self._lock:
            if ttl is None:
                ttl = self.config.default_ttl
                
            item = CacheItem(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                size=len(str(value))  # Rough size estimate
            )
            
            success = self._backend.set(key, item)
            if success:
                self._stats['sets'] += 1
            return success
            
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted
        """
        with self._lock:
            success = self._backend.delete(key)
            if success:
                self._stats['deletes'] += 1
            return success
            
    def clear(self):
        """Clear all items from cache."""
        with self._lock:
            self._backend.clear()
            
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.get(key) is not None
        
    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs for found items
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
        
    def mset(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple items in cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if all items were set successfully
        """
        success = True
        for key, value in items.items():
            if not self.set(key, value, ttl):
                success = False
        return success
        
    def get_or_set(self, key: str, factory: Callable[[], Any], 
                   ttl: Optional[int] = None) -> Any:
        """
        Get value from cache or set it using factory function.
        
        Args:
            key: Cache key
            factory: Function to generate value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or newly generated value
        """
        value = self.get(key)
        if value is not None:
            return value
            
        # Generate new value
        value = factory()
        self.set(key, value, ttl)
        return value
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                'size': self._backend.size(),
                'config': asdict(self.config),
                'hit_rate': (
                    stats['hits'] / (stats['hits'] + stats['misses'])
                    if stats['hits'] + stats['misses'] > 0 else 0
                )
            })
            return stats
            
    def _cleanup_loop(self):
        """Background cleanup loop to remove expired items."""
        while True:
            try:
                time.sleep(self.config.cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                
    def _cleanup_expired(self):
        """Remove expired items from cache."""
        if self.config.backend == CacheBackend.SQLITE:
            # For SQLite, we can cleanup efficiently
            with sqlite3.connect(self.config.sqlite_db_path) as conn:
                current_time = time.time()
                cursor = conn.execute(
                    'DELETE FROM cache WHERE ttl > 0 AND (created_at + ttl) < ?',
                    (current_time,)
                )
                if cursor.rowcount > 0:
                    self._stats['evictions'] += cursor.rowcount
                    logger.debug(f"Cleaned up {cursor.rowcount} expired cache items")


# Decorator for caching function results
def cached(ttl: int = 3600, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from args/kwargs
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "|".join(key_parts)
                
            # Try to get from cache
            if hasattr(func, '_cache_service'):
                cache = func._cache_service
                result = cache.get(cache_key)
                if result is not None:
                    return result
                    
                # Not in cache, compute result
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                return result
            else:
                # No cache service, just call function
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


# Cache service instance (singleton pattern)
_cache_service_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService()
    return _cache_service_instance


def init_cache_service(config: Optional[CacheConfig] = None):
    """Initialize global cache service with configuration."""
    global _cache_service_instance
    _cache_service_instance = CacheService(config)


# Example usage for web diagnostics
if __name__ == "__main__":
    # Initialize cache service
    config = CacheConfig(
        backend=CacheBackend.SQLITE,
        max_size=5000,
        default_ttl=1800,  # 30 minutes
        cleanup_interval=600  # 10 minutes
    )
    
    cache = CacheService(config)
    
    # Example: Cache analysis results
    def analyze_website(url: str) -> Dict[str, Any]:
        """Simulate website analysis."""
        print(f"Analyzing {url}...")
        time.sleep(1)  # Simulate work
        return {
            "url": url,
            "status": "analyzed",
            "score": 85,
            "timestamp": time.time()
        }
    
    # Cache analysis results
    url = "https://example.com"
    cache_key = f"analysis:{url}"
    
    # First call - will analyze
    result1 = cache.get_or_set(cache_key, lambda: analyze_website(url), ttl=3600)
    print(f"Result 1: {result1}")
    
    # Second call - will use cache
    result2 = cache.get(cache_key)
    print(f"Result 2: {result2}")
    
    # Print statistics
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")
    
    # Example with decorator
    cache_service = get_cache_service()
    
    @cached(ttl=1800)
    def expensive_analysis(domain: str, check_type: str):
        print(f"Performing {check_type} analysis on {domain}")
        time.sleep(0.5)  # Simulate work
        return f"Analysis result for {domain} ({check_type})"
    
    # Attach cache service to function
    expensive_analysis._cache_service = cache_service
    
    # Test cached function
    result = expensive_analysis("example.com", "seo")
    print(f"Cached function result: {result}")
    
    # Second call should use cache
    result2 = expensive_analysis("example.com", "seo")
    print(f"Cached function result (cached): {result2}")