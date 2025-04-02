import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from api.utils.logger import logger, log_llm_call, log_llm_response

# Initialize OpenAI client with API key
client = AsyncOpenAI(api_key=os.getenv("GPT_API_KEY"))

async def call_gpt(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call GPT model with the given prompt using the new OpenAI API syntax
    """
    try:
        log_llm_call("gpt", prompt)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        text = response.choices[0].message.content
        log_llm_response("gpt", text)
        
        return {
            "text": text,
            "model": "gpt",
            "success": True,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        error_msg = f"Error calling GPT: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "gpt",
            "success": False
        }