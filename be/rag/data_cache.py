# backend/rag/data_cache.py
"""
Simple in-memory cache for downloaded attachment data
"""
import pandas as pd
import io
from typing import Dict, Optional, Tuple
import hashlib

# Global cache for downloaded data
_data_cache: Dict[str, bytes] = {}
_dataframe_cache: Dict[str, pd.DataFrame] = {}

def _cache_key(blob_uri: str, filename: str) -> str:
    """Generate cache key from blob URI and filename"""
    key_data = f"{blob_uri}:{filename}".encode('utf-8')
    return hashlib.md5(key_data).hexdigest()

def cache_blob_data(blob_uri: str, filename: str, data: bytes):
    """Cache downloaded blob data"""
    key = _cache_key(blob_uri, filename)
    _data_cache[key] = data
    print(f"[CACHE] Stored {len(data)} bytes for {filename}")

def get_cached_blob_data(blob_uri: str, filename: str) -> Optional[bytes]:
    """Get cached blob data"""
    key = _cache_key(blob_uri, filename)
    data = _data_cache.get(key)
    if data:
        print(f"[CACHE] Found {len(data)} bytes for {filename}")
    return data

def cache_dataframe(blob_uri: str, filename: str, sheet: Optional[str], df: pd.DataFrame):
    """Cache processed DataFrame"""
    cache_key = f"{_cache_key(blob_uri, filename)}:{sheet or 'default'}"
    _dataframe_cache[cache_key] = df.copy()
    print(f"[CACHE] Stored DataFrame {df.shape} for {filename}:{sheet}")

def get_cached_dataframe(blob_uri: str, filename: str, sheet: Optional[str]) -> Optional[pd.DataFrame]:
    """Get cached DataFrame"""
    cache_key = f"{_cache_key(blob_uri, filename)}:{sheet or 'default'}"
    df = _dataframe_cache.get(cache_key)
    if df is not None:
        print(f"[CACHE] Found DataFrame {df.shape} for {filename}:{sheet}")
        return df.copy()
    return None

def clear_cache():
    """Clear all cached data"""
    global _data_cache, _dataframe_cache
    data_count = len(_data_cache)
    df_count = len(_dataframe_cache)
    _data_cache.clear()
    _dataframe_cache.clear()
    print(f"[CACHE] Cleared {data_count} blob entries and {df_count} DataFrame entries")

def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics"""
    return {
        "blob_entries": len(_data_cache),
        "dataframe_entries": len(_dataframe_cache),
        "total_blob_size": sum(len(data) for data in _data_cache.values())
    }
