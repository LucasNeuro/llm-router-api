from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from loguru import logger
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import supabase, save_llm_data
from ..utils.conversation_memory import conversation_manager
import uuid
import json
import base64
from ..utils.audio_service import AudioService
import os
import tempfile
import aiofiles

router = APIRouter()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    prompt: str
    sender_phone: Optional[str] = None
    model: Optional[str] = None
    generate_audio: Optional[bool] = False

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
    """Limpa memórias antigas em background"""
    try:
        await conversation_manager.cleanup_inactive_sessions(max_age_hours=24)
    except Exception as e:
        logger.error(f"Erro ao limpar memórias antigas: {str(e)}")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint principal de chat que processa texto e opcionalmente gera áudio."""
    try:
        # Gera um ID único para a requisição
        request_id = str(uuid.uuid4())
        logger.info(f"Nova requisição de chat: {request_id}")

        # Roteamento do prompt
        router = LLMRouter()
        response = await router.route_prompt(
            prompt=request.prompt,
            sender_phone=request.sender_phone,
            model=request.model
        )

        # Se solicitado, gera áudio da resposta
        if request.generate_audio and response.get("text"):
            try:
                audio_result = await AudioService.text_to_speech(
                    text=response["text"],
                    request_id=request_id
                )
                response["audio"] = audio_result
            except Exception as e:
                logger.error(f"Erro ao gerar áudio: {str(e)}")
                response["audio_error"] = str(e)

        return response

    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/audio")
async def audio_chat_endpoint(
    audio: UploadFile = File(...),
    sender_phone: Optional[str] = Form(None),
    model: Optional[str] = None,
    generate_audio: Optional[bool] = Form(False)
):
    """Endpoint que recebe áudio, transcreve e processa como chat."""
    try:
        # Gera um ID único para a requisição
        request_id = str(uuid.uuid4())
        logger.info(f"Nova requisição de áudio: {request_id}")

        # Salva o arquivo de áudio temporariamente
        temp_path = AudioService.get_temp_path(f"upload_{request_id}.mp3")
        try:
            with open(temp_path, "wb") as f:
                content = await audio.read()
                f.write(content)
            logger.info(f"Áudio salvo temporariamente em: {temp_path}")

            # Transcreve o áudio
            transcription = await AudioService.speech_to_text(temp_path, request_id)
            if not transcription.get("text"):
                raise HTTPException(status_code=400, detail="Falha ao transcrever áudio")

            # Processa o texto transcrito
            router = LLMRouter()
            response = await router.route_prompt(
                prompt=transcription["text"],
                sender_phone=sender_phone,
                model=model
            )

            # Adiciona informação da transcrição à resposta
            response["transcription"] = transcription["text"]

            # Se solicitado, gera áudio da resposta
            if generate_audio and response.get("text"):
                try:
                    audio_result = await AudioService.text_to_speech(
                        text=response["text"],
                        request_id=f"{request_id}_response"
                    )
                    response["audio"] = audio_result
                except Exception as e:
                    logger.error(f"Erro ao gerar áudio da resposta: {str(e)}")
                    response["audio_error"] = str(e)

            return response

        finally:
            # Limpa o arquivo temporário
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Arquivo temporário removido: {temp_path}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")

    except Exception as e:
        logger.error(f"Erro no endpoint de áudio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/clear-memory")
async def clear_memory_endpoint(sender_phone: str):
    """Limpa o histórico de conversa para um número específico."""
    try:
        supabase.table("conversation_history").delete().eq("sender_phone", sender_phone).execute()
        return {"message": f"Memória limpa para {sender_phone}"}
    except Exception as e:
        logger.error(f"Erro ao limpar memória: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))