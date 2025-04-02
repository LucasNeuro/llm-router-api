from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.utils.logger import logger
from ..llm_router.router import LLMRouter

router = APIRouter()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    text: str
    model: str
    success: bool = True
    task_type: Optional[str] = None
    confidence: Optional[float] = None
    model_scores: Optional[Dict[str, float]] = None
    complexity: Optional[str] = None
    indicators: Optional[Dict[str, int]] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that routes requests to the appropriate LLM
    """
    try:
        logger.info(f"Received chat request: {request.prompt[:100]}...")
        
        response = await llm_router.route(prompt=request.prompt)
        
        # Extract classification info if available
        classification = response.get("classification", {})
        metadata = classification.get("metadata", {})
        
        return ChatResponse(
            text=response["text"],
            model=response.get("model", "unknown"),
            success=response.get("success", True),
            task_type=classification.get("task_type"),
            confidence=classification.get("confidence"),
            model_scores=metadata.get("model_scores"),
            complexity=metadata.get("complexity"),
            indicators={
                "complex": metadata.get("complex_indicators_found", 0),
                "technical": metadata.get("technical_indicators_found", 0),
                "creative": metadata.get("creative_indicators_found", 0),
                "practical": metadata.get("practical_indicators_found", 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )