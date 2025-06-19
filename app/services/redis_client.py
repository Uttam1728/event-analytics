import redis.asyncio as redis
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for managing connections and operations."""
    
    _instance: Optional['RedisClient'] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish Redis connection."""
        if self._redis is None:
            try:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
                print(redis_url)
                self._redis = redis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("Successfully connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._redis is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._redis
    
    async def increment_minute_bucket(self, minute_key: str, user_id: str) -> int:
        """
        Increment the count for a minute bucket.
        If key doesn't exist, create it with TTL of 5 minutes.
        
        Args:
            minute_key: The key for the minute bucket
            user_id: The user ID to add to the users set
            
        Returns:
            The new count value
        """
        try:
            # Use pipeline for atomic operations
            async with self._redis.pipeline() as pipe:
                # Check if main minute key exists
                exists = await self._redis.exists(minute_key)
                
                if not exists:
                    # Key doesn't exist, set it to 1 with 5 minute TTL
                    await pipe.setex(minute_key, 300, 1)  # 300 seconds = 5 minutes
                    logger.debug(f"Created new minute bucket: {minute_key} with count 1")
                    new_count = 1
                else:
                    # Key exists, increment it
                    new_count = await self._redis.incr(minute_key)
                    logger.debug(f"Incremented minute bucket: {minute_key} to count {new_count}")
                
                # Handle user tracking
                user_key = f"{minute_key}:users"
                user_exists = await self._redis.exists(user_key)
                
                if not user_exists:
                    # Create new user set with TTL
                    await pipe.sadd(user_key, user_id)
                    await pipe.expire(user_key, 300)  # Set TTL without overwriting the set
                    logger.debug(f"Created new user set: {user_key} with user {user_id}")
                else:
                    # Add user to existing set
                    await pipe.sadd(user_key, user_id)
                    logger.debug(f"Added user {user_id} to existing set: {user_key}")
                
                await pipe.execute()
                return new_count

        except Exception as e:
            logger.error(f"Error updating minute bucket {minute_key}: {e}")
            raise
    
    # param : user id and minute key and in key it will add user id 
    async def add_minute_bucket_with_user_id(self, user_id: str, minute_key: str) -> int:
        """
        Increment the count for a minute bucket and add the user ID to the set.
        If key doesn't exist, create it with TTL of 5 minutes.
        
        Args:
            user_id: The user ID to add to the set
            minute_key: The key for the minute bucket
            
        Returns:
            The new count value
        """
        try:
            # Use pipeline for atomic operations
            async with self._redis.pipeline() as pipe:
                # Check if key exists
                exists = await pipe.exists(minute_key).execute()
                
                if not exists:
                    # Key doesn't exist, set it to 1 with 5 minute TTL and add user ID to set
                    await pipe.setex(minute_key, 300, 1)  # 300 seconds = 5 minutes
                    await pipe.sadd(minute_key, user_id)
                    await pipe.execute()
                    logger.debug(f"Created new minute bucket: {minute_key} with count 1 and added user ID {user_id}")
                    return 1
                else:
                    # Key exists, increment it and add user ID to set
                    await pipe.sadd(minute_key, user_id)
                    await pipe.execute()
                    # logger.debug(f"Incremented minute bucket: {minute_key} to count {new_count} and added user ID {user_id}")
                    return 1
                    
        except Exception as e:
            logger.error(f"Error updating minute bucket {minute_key} with user ID {user_id}: {e}")
            raise

    async def get_minute_bucket_count(self, minute_key: str) -> int:
        """
        Get the current count for a minute bucket.
        
        Args:
            minute_key: The key for the minute bucket
            
        Returns:
            The current count (0 if key doesn't exist)
        """
        try:
            count = await self._redis.get(minute_key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting minute bucket count {minute_key}: {e}")
            return 0

    async def get_minute_bucket_users(self, minute_key: str) -> list:
        """
        Get the users for a minute bucket.
        
        Args:
            minute_key: The key for the minute bucket
            
        Returns:
            A list of users in the minute bucket
        """
        try:
            users = await self._redis.smembers(f"{minute_key}:users")
            return list(users)
        except Exception as e:
            logger.error(f"Error getting minute bucket users {minute_key}: {e}")
            return []

        
            
# Global instance
redis_client = RedisClient() 