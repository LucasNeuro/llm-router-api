from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from api.utils.logger import logger
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
import uuid

router = APIRouter()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None

class CostDetail(BaseModel):
    cents: int
    dollars: int
    formatted: str

class Costs(BaseModel):
    usd: CostDetail
    brl: CostDetail

class CostAnalysis(BaseModel):
    model: str
    model_info: Dict[str, Any]
    tokens: Dict[str, int]
    costs: Costs
    pricing: Dict[str, float]

class ChatResponse(BaseModel):
    text: str
    model: str
    success: bool
    confidence: Optional[float] = None
    model_scores: Optional[Dict[str, float]] = None
    indicators: Optional[Dict[str, bool]] = None
    cost_analysis: Optional[CostAnalysis] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Gera um ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Log da requisição recebida
        logger.info(f"Requisição recebida - ID: {request_id}")
        logger.info(f"Prompt: {request.prompt}")
        logger.info(f"Modelo especificado: {request.model}")
        
        # Processa a requisição
        result = await llm_router.route_prompt(request.prompt, request.model)
        
        # Analisa custos
        cost_analysis = analyze_cost(result["model"], request.prompt, result["text"])
        
        # Prepara resposta
        response_data = {
            "text": result["text"],
            "model": result["model"],
            "success": result["success"],
            "confidence": result.get("confidence"),
            "model_scores": result.get("model_scores"),
            "indicators": result.get("indicators"),
            "cost_analysis": cost_analysis
        }
        
        # Cria objeto ChatResponse
        response = ChatResponse(**response_data)
        
        # Salva dados no Supabase
        await save_llm_data(
            prompt=request.prompt,
            response=response.text,
            model=response.model,
            success=response.success,
            confidence=response.confidence,
            scores=response.model_scores or {},
            indicators=response.indicators or {},
            cost_analysis=cost_analysis,
            request_id=request_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))