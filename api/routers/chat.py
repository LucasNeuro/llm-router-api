from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
from ..utils.conversation_memory import conversation_manager
from api.utils.logger import logger

router = APIRouter()
llm_router = LLMRouter()

class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    sender: Optional[str] = None

async def handle_memory_command(prompt: str, sender: str) -> Optional[Dict[str, Any]]:
    """Processa comandos especiais de memória"""
    commands = {
        "/memory off": (False, "Memória desativada. O contexto anterior será ignorado."),
        "/memory on": (True, "Memória ativada. O contexto será mantido."),
        "/memory clear": (None, "Memória limpa. Todas as mensagens anteriores foram removidas.")
    }
    
    prompt_lower = prompt.lower().strip()
    if prompt_lower in commands:
        active, message = commands[prompt_lower]
        
        if active is None:
            # Comando de limpar
            await conversation_manager.clear_memory(sender)
        else:
            # Comando de ativar/desativar
            await conversation_manager.toggle_memory(sender, active)
            
        return {
            "text": message,
            "model": "system",
            "success": True
        }
    
    return None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint para chat com LLM Router
    """
    try:
        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())
        
        # Log da requisição
        logger.info(f"Requisição recebida - ID: {request_id}")
        logger.info(f"Prompt: {request.prompt}")
        logger.info(f"Modelo especificado: {request.model}")
        
        # Se tiver um remetente, verifica comandos de memória
        if request.sender:
            command_result = await handle_memory_command(request.prompt, request.sender)
            if command_result:
                return command_result
            
            # Salva a mensagem do usuário na memória
            await conversation_manager.add_message(
                sender_phone=request.sender,
                role="user",
                content=request.prompt
            )

        # Usa o LLM Router
        result = await llm_router.route_prompt(
            prompt=request.prompt,
            model=request.model,
            sender_phone=request.sender
        )
        
        # Se tiver um remetente, salva a resposta do assistente na memória
        if request.sender:
            await conversation_manager.add_message(
                sender_phone=request.sender,
                role="assistant",
                content=result["text"],
                model_used=result["model"]
            )

        # Analisa custos
        cost_analysis = analyze_cost(result["model"], request.prompt, result["text"])
        
        # Salva dados no Supabase
        await save_llm_data(
            prompt=request.prompt,
            response=result["text"],
            model=result["model"],
            success=result["success"],
            confidence=result.get("confidence"),
            scores=result.get("model_scores", {}),
            indicators=result.get("indicators", {}),
            cost_analysis=cost_analysis,
            request_id=request_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))