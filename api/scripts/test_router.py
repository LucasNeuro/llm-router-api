import asyncio
import logging
from llm_router.router import LLMRouter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_router():
    """Test the LLM router with different prompts"""
    router = LLMRouter()
    
    test_cases = [
        {
            "prompt": "Write a Python function to calculate Fibonacci numbers",
            "expected_model": "deepseek"
        },
        {
            "prompt": "Write a creative story about a magical forest",
            "expected_model": "mistral"
        },
        {
            "prompt": "Explain how quantum computers work",
            "expected_model": "gemini"
        },
        {
            "prompt": "Analyze the implications of artificial general intelligence on society",
            "expected_model": "gpt"
        }
    ]
    
    for case in test_cases:
        logger.info(f"\nTesting prompt: {case['prompt']}")
        try:
            response = await router.route(case["prompt"])
            logger.info(f"Response from model: {response.get('model', 'unknown')}")
            logger.info(f"Classification: {response.get('classification', {})}")
            logger.info(f"Response text: {response.get('text', '')[:100]}...")
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_router()) 