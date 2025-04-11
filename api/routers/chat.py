from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from api.utils.logger import logger
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import supabase, save_llm_data
from ..utils.conversation_memory import conversation_manager
import uuid

router = APIRouter()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    prompt: str
    sender_phone: Optional[str] = None
    model: Optional[str] = None
    clear_memory: Optional[bool] = False

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
    has_memory: Optional[bool] = True

async def cleanup_old_memories(background_tasks: BackgroundTasks):
    """Tarefa em background para limpar memórias antigas (mais de 30 dias)"""
    await conversation_manager.cleanup_old_memories(days=30)

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        # Adiciona tarefa de limpeza em background
        background_tasks.add_task(cleanup_old_memories, background_tasks)
        
        # Gera um ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Log da requisição recebida
        logger.info(f"Requisição recebida - ID: {request_id}")
        logger.info(f"Prompt: {request.prompt}")
        logger.info(f"Modelo especificado: {request.model}")
        
        # Processa a requisição
        result = await llm_router.route_prompt(
            prompt=request.prompt,
            sender_phone=request.sender_phone,
            model=request.model
        )
        
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
            "cost_analysis": cost_analysis,
            "has_memory": bool(request.sender_phone)
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

@router.delete("/clear-memory/{sender_phone}")
async def clear_memory(sender_phone: str):
    """Endpoint para limpar a memória de um número específico"""
    try:
        # Cria um novo registro vazio para o número
        data = {
            "conversation_memory": {"messages": []}
        }
        supabase.table("conversation_memory")\
            .update(data)\
            .eq("sender_phone", sender_phone)\
            .execute()
        return {"message": "Memória limpa com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao limpar memória: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))