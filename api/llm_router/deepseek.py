import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Initialize OpenAI client with API key
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

async def call_deepseek(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Deepseek model with the given prompt
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        text = response.choices[0].message.content
        
        return {
            "text": text,
            "model": "deepseek",
            "success": True,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        error_msg = f"Error calling Deepseek: {str(e)}"
        return {
            "text": error_msg,
            "model": "deepseek",
            "success": False
        }