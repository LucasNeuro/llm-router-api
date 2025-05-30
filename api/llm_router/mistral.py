import os
from typing import Dict, Any, Optional
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

async def call_mistral(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Mistral model with the given prompt
    """
    try:
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        response = client.chat(
            model="mistral-large-latest",
            messages=messages
        )

        text = response.choices[0].message.content
        
        return {
            "text": text,
            "model": "mistral",
            "success": True,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        error_msg = f"Error calling Mistral: {str(e)}"
        return {
            "text": error_msg,
            "model": "mistral",
            "success": False
        }