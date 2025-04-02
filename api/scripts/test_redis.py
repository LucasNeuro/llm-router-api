import logging
from redis_cache.cache import RedisGraphCache
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_redis_connection():
    """Test Redis connection and basic operations"""
    cache = RedisGraphCache()
    
    # Test data
    test_prompt = "What is Python?"
    test_response = "Python is a high-level programming language."
    test_model = "gemini"
    
    try:
        # Test caching
        logger.info("Testing cache write...")
        success = cache.cache_response(
            text=test_prompt,
            response=test_response,
            model=test_model,
            tokens=20,
            latency=0.5
        )
        
        if not success:
            logger.error("Failed to write to cache")
            return False
            
        # Test retrieval
        logger.info("Testing cache read...")
        cached = cache.get_cached_response(
            text=test_prompt,
            model=test_model
        )
        
        if not cached:
            logger.error("Failed to read from cache")
            return False
            
        logger.info(f"Retrieved response: {cached['text']}")
        
        # Test stats
        logger.info("Testing cache stats...")
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats}")
        
        logger.info("All tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_redis_connection() 