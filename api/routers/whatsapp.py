from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
from ..utils.conversation_memory import conversation_manager
import uuid
import json
from api.utils.logger import logger
import time

router = APIRouter()
llm_router = LLMRouter()

# Configurações da MegaAPI
MEGAAPI_INSTANCE_ID = os.getenv("MEGAAPI_INSTANCE_ID")
MEGAAPI_API_KEY = os.getenv("MEGAAPI_API_KEY")
MEGAAPI_BASE_URL = os.getenv("MEGAAPI_BASE_URL", "https://apibusiness1.megaapi.com.br")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL", "https://hook.us2.make.com/hrq5lp1ahhw916uq0tdrqlr8dcmkcs64")

# Cache para evitar duplicação de mensagens
processed_messages = set()

if not MEGAAPI_INSTANCE_ID or not MEGAAPI_API_KEY:
    raise ValueError("MEGAAPI_INSTANCE_ID e MEGAAPI_API_KEY precisam estar configurados")

class WhatsAppMessage(BaseModel):
    messageType: str
    text: Optional[str] = None
    phone: str
    instanceId: str
    messageId: str
    timestamp: int

async def send_whatsapp_message(phone: str, message: str):
    """
    Envia mensagem via MegaAPI
    """
    try:
        # Formata o número do telefone
        if not phone.startswith("55"):
            phone = f"55{phone}"
            
        url = f"{MEGAAPI_BASE_URL}/rest/sendMessage/megabusiness-MoYuzQehcPQ/text"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
        }
        payload = {
            "messageData": {
                "to": phone,
                "text": message
            }
        }

        logger.info(f"Enviando mensagem para {phone}")
        logger.info(f"URL: {url}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Resposta do envio: {json.dumps(response_data, indent=2)}")
            return response_data

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {str(e)}")

async def send_to_make(phone: str, message: str, original_message: str, model: str = None):
    """
    Envia mensagem processada para o webhook do Make
    """
    try:
        # Garante que o telefone está no formato correto
        if phone.startswith("55"):
            phone = phone[2:]
            
        payload = {
            "phone": phone,
            "response": message,
            "original_message": original_message,
            "model": model or "Não especificado",
            "timestamp": int(time.time())
        }

        logger.info(f"Enviando para Make webhook: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                MAKE_WEBHOOK_URL, 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Log da resposta bruta para debug
            logger.info(f"Resposta bruta do Make: {response.text}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"Resposta do Make webhook: {json.dumps(response_data, indent=2)}")
                    return response_data
                except json.JSONDecodeError:
                    # Se a resposta for "Accepted" mas não for JSON, ainda é válido
                    if response.text.strip() == "Accepted":
                        logger.info("Make webhook aceitou a requisição com resposta 'Accepted'")
                        return {"status": "accepted"}
                    raise
            else:
                response.raise_for_status()

    except Exception as e:
        logger.error(f"Erro ao enviar para Make webhook: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        # Não lança exceção HTTP aqui para não interromper o fluxo principal
        logger.warning("Continuando execução mesmo com erro no Make webhook")
        return {"status": "error", "detail": str(e)}

async def cleanup_sessions(background_tasks: BackgroundTasks):
    """Tarefa em background para limpar sessões inativas"""
    await conversation_manager.cleanup_inactive_sessions()

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook para receber mensagens do WhatsApp
    """
    try:
        # Adiciona tarefa de limpeza em background
        background_tasks.add_task(cleanup_sessions, background_tasks)
        
        # Log do corpo da requisição bruto
        body = await request.body()
        logger.info(f"Corpo da requisição bruto: {body.decode()}")

        # Tenta fazer o parse do JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Corpo da requisição que causou erro: {body.decode()}")
            return {"status": "error", "reason": "invalid_json"}

        logger.info(f"Webhook recebido: {json.dumps(payload, indent=2)}")

        # Verifica se é uma mensagem do próprio bot ou confirmação
        if (payload.get("messageType") == "message.ack" or
            (payload.get("key", {}).get("fromMe", False) and "instance_key" in payload)):
            logger.info("Mensagem de confirmação ou do bot, ignorando")
            return {"status": "ignored", "reason": "bot_message"}

        # Extrai o ID da mensagem para deduplicação
        message_id = payload.get("key", {}).get("id")
        if message_id in processed_messages:
            logger.info(f"Mensagem {message_id} já processada, ignorando")
            return {"status": "ignored", "reason": "duplicate_message"}
        
        # Adiciona mensagem ao cache de processadas
        if message_id:
            processed_messages.add(message_id)
            # Limita o tamanho do cache
            if len(processed_messages) > 1000:
                processed_messages.clear()

        # Verifica se é uma mensagem válida
        if not isinstance(payload, dict):
            logger.error(f"Payload inválido, não é um dicionário: {payload}")
            return {"status": "error", "reason": "invalid_payload"}

        # Verifica se tem a mensagem
        if not payload.get("message"):
            logger.info("Não é uma mensagem de texto, ignorando")
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai a mensagem do campo correto
        message_text = None
        message_data = payload.get("message", {})
        
        if isinstance(message_data, dict):
            if "extendedTextMessage" in message_data:
                message_text = message_data["extendedTextMessage"].get("text", "")
            elif "conversation" in message_data:
                message_text = message_data["conversation"]
            elif "text" in message_data:
                message_text = message_data["text"].get("message", "")

        # Se não houver mensagem de texto, ignora
        if not message_text:
            logger.info(f"Mensagem sem texto extraível: {json.dumps(message_data, indent=2)}")
            return {"status": "ignored", "reason": "no_text_content"}

        # Log da mensagem extraída
        logger.info(f"Mensagem extraída com sucesso: {message_text}")

        # Extrai informações da mensagem
        try:
            # Extrai o número do remetente do remoteJid
            phone = payload.get("key", {}).get("remoteJid", "").split("@")[0]
            # Remove o prefixo "55" se existir
            if phone.startswith("55"):
                phone = phone[2:]
                
            # Processa o timestamp corretamente
            timestamp = payload.get("messageTimestamp")
            if isinstance(timestamp, dict) and "low" in timestamp:
                timestamp = timestamp["low"]
            elif not isinstance(timestamp, int):
                timestamp = int(time.time())
            
            message = WhatsAppMessage(
                messageType=payload.get("messageType", "text"),
                text=message_text,
                phone=phone,
                instanceId=payload.get("instance_key", ""),
                messageId=payload.get("key", {}).get("id", ""),
                timestamp=timestamp
            )
            
            # Log do número do remetente
            logger.info(f"Número do remetente: {phone}")

            # Salva a mensagem do usuário na memória
            await conversation_manager.add_message(
                sender_phone=phone,
                role="user",
                content=message_text
            )
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações da mensagem: {str(e)}")
            return {"status": "error", "reason": "invalid_message_format"}

        # Processa a mensagem com o LLM Router
        try:
            logger.info(f"Iniciando processamento LLM Router para mensagem: {message.text}")
            
            # Remove instruções anteriores se existirem
            clean_text = message.text
            if "Por favor, responda em português do Brasil" in clean_text:
                clean_text = message.text.split("Por favor, responda em português do Brasil")[0].strip()
            if "Lembre-se:" in clean_text:
                clean_text = clean_text.split("Lembre-se:")[0].strip()
            
            # Força resposta em português do Brasil e trata como pergunta
            prompt_ptbr = f"""Por favor, responda em português do Brasil de forma natural e coloquial a seguinte mensagem:

{clean_text}

Lembre-se:
1. Mantenha o tom natural e amigável
2. Seja prestativo e forneça informações relevantes
3. Use linguagem coloquial do Brasil"""

            # Usa o LLM Router com contexto da conversa
            result = await llm_router.route_prompt(
                prompt=prompt_ptbr,
                sender_phone=message.phone
            )
            
            logger.info(f"Resposta do LLM Router: {json.dumps(result, indent=2)}")

            # Salva a resposta do assistente na memória
            await conversation_manager.add_message(
                sender_phone=message.phone,
                role="assistant",
                content=result["text"],
                model_used=result["model"]
            )

            # Gera ID único para a requisição
            request_id = str(uuid.uuid4())

            # Analisa custos
            cost_analysis = analyze_cost(result["model"], prompt_ptbr, result["text"])

            # Salva dados no Supabase
            await save_llm_data(
                prompt=message.text,
                response=result["text"],
                model=result["model"],
                success=result["success"],
                confidence=result.get("confidence"),
                scores=result.get("model_scores", {}),
                indicators=result.get("indicators", {}),
                cost_analysis=cost_analysis,
                request_id=request_id
            )

            # Envia para o webhook do Make com o modelo usado
            await send_to_make(
                phone=message.phone, 
                message=result["text"], 
                original_message=message.text,
                model=result["model"]
            )

            # Envia resposta via WhatsApp
            await send_whatsapp_message(message.phone, result["text"])

            return {
                "status": "success",
                "messageId": message.messageId,
                "model": result["model"],
                "has_context": result.get("has_context", False)
            }

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            # Em caso de erro, tenta enviar uma mensagem de erro para o usuário
            try:
                error_message = "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?"
                await send_whatsapp_message(message.phone, error_message)
            except:
                pass
            return {"status": "error", "reason": str(e)}

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return {"status": "error", "reason": str(e)}

@router.get("/whatsapp/status")
async def whatsapp_status():
    """
    Verifica status da conexão com WhatsApp
    """
    try:
        url = f"{MEGAAPI_BASE_URL}/rest/instance/status"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json"
        }
        params = {
            "instanceId": "megabusiness-MoYuzQehcPQ"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            status = response.json()

        return {
            "status": "success",
            "instance_id": "megabusiness-MoYuzQehcPQ",
            "whatsapp_status": status
        }

    except Exception as e:
        logger.error(f"Erro ao verificar status: {str(e)}")
        return {
            "status": "error",
            "instance_id": "megabusiness-MoYuzQehcPQ",
            "error": str(e)
        }