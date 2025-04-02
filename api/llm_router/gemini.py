import os
from typing import Dict, Any, Optional
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def call_gemini(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Gemini model with the given prompt
    """
    try:
        # Combine system prompt and user prompt if system prompt exists
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(full_prompt)
        
        return {
            "text": response.text,
            "model": "gemini",
            "success": True
        }
        
    except Exception as e:
        error_msg = f"Error calling Gemini: {str(e)}"
        return {
            "text": error_msg,
            "model": "gemini",
            "success": False
        }