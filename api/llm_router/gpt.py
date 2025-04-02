import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

# Initialize OpenAI client with API key
GPT_API_KEY = os.getenv("GPT_API_KEY")
client = AsyncOpenAI(api_key=GPT_API_KEY) if GPT_API_KEY else None

async def call_gpt(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call GPT model with the given prompt using the new OpenAI API syntax
    """
    try:
        if not GPT_API_KEY:
            return {
                "text": "GPT_API_KEY não configurada",
                "model": "gpt",
                "success": False
            }
            
        if not client:
            return {
                "text": "Cliente OpenAI não inicializado",
                "model": "gpt",
                "success": False
            }
            
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