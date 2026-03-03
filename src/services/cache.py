import json
from typing import Optional
import redis.asyncio as redis
import os


class CacheService:
    """Redis cache service for frequently accessed links"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self.cache_ttl = 3600  # 1 hour cache expiration
    
    async def connect(self):
        """establish connection to redis"""
        try:
            self.client = await redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            print("✓ Redis connected successfully")
        except Exception as e:
            print(f"⚠ Warning: Redis connection failed: {e}")
            self.client = None
    
    async def disconnect(self):
        """close redis connection"""
        if self.client:
            await self.client.close()
            print("✓ Redis disconnected")
    
    async def get_link(self, short_code: str) -> Optional[dict]:
        """retrieve cached link data"""
        if not self.client:
            return None
        
        try:
            data = await self.client.get(f"link:{short_code}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set_link(self, short_code: str, link_data: dict):
        """cache link data with TTL"""
        if not self.client:
            return
        
        try:
            await self.client.setex(
                f"link:{short_code}",
                self.cache_ttl,
                json.dumps(link_data)
            )
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def delete_link(self, short_code: str):
        """invalidate link cache"""
        if not self.client:
            return
        
        try:
            await self.client.delete(f"link:{short_code}")
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    async def increment_click_count(self, short_code: str) -> int:
        """increment click count in cache"""
        if not self.client:
            return 0
        
        try:
            count = await self.client.incr(f"clicks:{short_code}")
            # set expiration if first time
            await self.client.expire(f"clicks:{short_code}", self.cache_ttl)
            return count
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0
    
    async def get_top_links(self, limit: int = 10, min_clicks: int = 1) -> list:
        """get most accessed links by click count (only links with actual clicks)"""
        if not self.client:
            return []
        
        try:
            # scan for all click keys and get their counts
            cursor = "0"
            links = []
            
            while True:
                cursor, keys = await self.client.scan(cursor, match="clicks:*", count=100)
                
                for key in keys:
                    short_code = key.replace("clicks:", "")
                    clicks_str = await self.client.get(key)
                    if clicks_str:
                        clicks = int(clicks_str)
                        # only include links with actual clicks (min_clicks threshold)
                        if clicks >= min_clicks:
                            links.append({
                                "short_code": short_code,
                                "clicks": clicks
                            })
                
                if cursor == "0":
                    break
            
            # sort by clicks descending, then by short_code for stability
            links.sort(key=lambda x: (-x["clicks"], x["short_code"]))
            return links[:limit]
        except Exception as e:
            print(f"Cache top links error: {e}")
            return []


# global cache instance
cache = CacheService()
