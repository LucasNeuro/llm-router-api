import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

# Initialize OpenAI client with API key
client = AsyncOpenAI(api_key=os.getenv("GPT_API_KEY"))

async def call_gpt(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call GPT model with the given prompt using the new OpenAI API syntax
    """
    try:
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
        return {
            "text": error_msg,
            "model": "gpt",
            "success": False
        }