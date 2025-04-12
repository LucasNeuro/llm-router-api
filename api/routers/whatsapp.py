from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import os
from ..llm_router.router import LLMRouter
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
from ..utils.conversation_memory import conversation_manager
from ..utils.audio_service import audio_service
import uuid
import json
from api.utils.logger import logger
import time
import base64

router = APIRouter()
llm_router = LLMRouter()

# Configurações da MegaAPI
MEGAAPI_INSTANCE_ID = os.getenv("MEGAAPI_INSTANCE_ID")
MEGAAPI_TOKEN = os.getenv("MEGAAPI_TOKEN")
MEGAAPI_HOST = os.getenv("MEGAAPI_HOST", "apibusiness1.megaapi.com.br")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

if not MEGAAPI_INSTANCE_ID or not MEGAAPI_TOKEN:
    raise ValueError("MEGAAPI_INSTANCE_ID e MEGAAPI_TOKEN precisam estar configurados")

class WhatsAppMessage(BaseModel):
    messageType: str
    text: Optional[str] = None
    audio: Optional[str] = None  # Base64 do áudio (se for mensagem de áudio)
    phone: str
    instanceId: str
    messageId: str
    timestamp: int
    is_audio: bool = False

async def send_whatsapp_message(phone: str, message: str):
    """
    Envia mensagem via MegaAPI
    """
    try:
        # Formata o número do telefone
        if not phone.startswith("55"):
            phone = f"55{phone}"
            
        url = f"{MEGAAPI_HOST}/rest/sendMessage/megabusiness-{MEGAAPI_TOKEN}/text"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json"
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

async def send_to_make(phone: str, message: str, original_message: str, model: str = None, is_audio: bool = False):
    """
    Envia mensagem processada para o webhook do Make
    """
    try:
        payload = {
            "phone": phone,
            "response": message,
            "original_message": original_message,
            "model": model or "Não especificado",
            "timestamp": int(time.time()),
            "is_audio": is_audio
        }

        logger.info(f"Enviando para Make webhook: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(MAKE_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Resposta do Make webhook: {json.dumps(response_data, indent=2)}")
            return response_data

    except Exception as e:
        logger.error(f"Erro ao enviar para Make webhook: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar para Make: {str(e)}")

async def send_whatsapp_audio(phone: str, audio_base64: str):
    """
    Envia mensagem de áudio via MegaAPI
    """
    try:
        # Formata o número do telefone
        if not phone.startswith("55"):
            phone = f"55{phone}"
            
        url = f"{MEGAAPI_HOST}/rest/sendMessage/megabusiness-{MEGAAPI_TOKEN}/audio"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json"
        }
        payload = {
            "messageData": {
                "to": phone,
                "audio": audio_base64
            }
        }

        logger.info(f"Enviando áudio para {phone}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Resposta do envio de áudio: {json.dumps(response_data, indent=2)}")
            return response_data

    except Exception as e:
        logger.error(f"Erro ao enviar áudio WhatsApp: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar áudio: {str(e)}")

async def cleanup_sessions(background_tasks: BackgroundTasks):
    """Tarefa em background para limpar sessões inativas"""
    await conversation_manager.cleanup_inactive_sessions()

async def extract_audio_from_message(message_data: Dict[str, Any]) -> Optional[str]:
    """
    Extrai dados de áudio da mensagem do WhatsApp
    
    Args:
        message_data: Dados da mensagem do WhatsApp
        
    Returns:
        Base64 do áudio ou None se não encontrado
    """
    try:
        # Verifica se tem mensagem de áudio
        if "audioMessage" in message_data:
            audio_data = message_data.get("audioMessage", {})
            
            # Verifica diferentes formatos que podem vir na API do WhatsApp
            if "data" in audio_data:
                return audio_data.get("data")
            elif "url" in audio_data:
                # Se for URL, faz download do áudio
                audio_url = audio_data.get("url")
                logger.info(f"Fazendo download de áudio da URL: {audio_url}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(audio_url)
                    if response.status_code == 200:
                        # Converte para base64
                        audio_bytes = response.content
                        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                        return base64_audio
            
        return None
        
    except Exception as e:
        logger.error(f"Erro ao extrair áudio da mensagem: {str(e)}")
        return None

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

        # Verifica se é uma mensagem válida
        if not isinstance(payload, dict):
            logger.error(f"Payload inválido, não é um dicionário: {payload}")
            return {"status": "error", "reason": "invalid_payload"}

        # Verifica se é uma mensagem de texto e não é um ACK
        if payload.get("messageType") == "message.ack":
            logger.info("É uma mensagem de confirmação (ACK), ignorando")
            return {"status": "ignored", "reason": "ack_message"}

        # Verifica se tem a mensagem
        message_data = payload.get("message", {})
        if not message_data:
            logger.info("Não é uma mensagem, ignorando")
            return {"status": "ignored", "reason": "not_message"}
            
        # Extrai o número do remetente
        try:
            # Extrai o número do remetente do remoteJid
            phone = payload.get("key", {}).get("remoteJid", "").split("@")[0]
            # Remove o prefixo "55" se existir
            if phone.startswith("55"):
                phone = phone[2:]
                
            logger.info(f"Número do remetente: {phone}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair número do remetente: {str(e)}")
            return {"status": "error", "reason": "invalid_phone_format"}
        
        # Verifica se é mensagem de áudio
        audio_base64 = await extract_audio_from_message(message_data)
        is_audio_message = audio_base64 is not None

        # Se for mensagem de áudio, transcreve
        message_text = None
        if is_audio_message:
            logger.info("Mensagem de áudio recebida, iniciando transcrição")
            
            # Salva o áudio em um arquivo temporário
            audio_file = await audio_service.save_base64_to_file(audio_base64)
            if not audio_file:
                logger.error("Erro ao salvar áudio em arquivo temporário")
                return {"status": "error", "reason": "audio_save_failed"}
                
            # Transcreve o áudio
            try:
                message_text = await audio_service.speech_to_text(audio_file)
                # Limpa o arquivo temporário
                audio_service.cleanup_temp_file(audio_file)
                
                if not message_text:
                    logger.error("Transcrição vazia")
                    message_text = "[Áudio sem conteúdo detectado]"
                    
                logger.info(f"Áudio transcrito: {message_text}")
                
            except Exception as e:
                logger.error(f"Erro na transcrição: {str(e)}")
                # Limpa o arquivo temporário em caso de erro
                audio_service.cleanup_temp_file(audio_file)
                return {"status": "error", "reason": f"transcription_failed: {str(e)}"}
        else:
            # Extrai a mensagem de texto
            if "extendedTextMessage" in message_data:
                message_text = message_data["extendedTextMessage"].get("text", "")
            elif "conversation" in message_data:
                message_text = message_data["conversation"]
            elif "text" in message_data:
                message_text = message_data["text"].get("message", "")

        # Se não houver mensagem de texto nem áudio, ignora
        if not message_text:
            logger.info("Mensagem sem texto ou áudio extraível")
            return {"status": "ignored", "reason": "no_content"}

        # Log da mensagem extraída
        logger.info(f"Mensagem extraída com sucesso: {message_text}")
        logger.info(f"Tipo de mensagem: {'Áudio' if is_audio_message else 'Texto'}")

        # Cria objeto de mensagem
        message = WhatsAppMessage(
            messageType=payload.get("messageType", "text"),
            text=message_text,
            phone=phone,
            instanceId=payload.get("instance_key", ""),
            messageId=payload.get("key", {}).get("id", ""),
            timestamp=payload.get("messageTimestamp", 0),
            is_audio=is_audio_message
        )

        # Processa a mensagem com o LLM Router
        try:
            logger.info(f"Iniciando processamento LLM Router para mensagem: {message.text}")
            
            # Força resposta em português do Brasil
            prompt_ptbr = f"""Por favor, responda em português do Brasil de forma natural e coloquial:

{message.text}

Lembre-se: Sua resposta DEVE ser em português do Brasil."""

            # Usa o LLM Router com contexto da conversa
            result = await llm_router.route_prompt(
                prompt=prompt_ptbr,
                sender_phone=phone,
                generate_audio=True,  # Sempre gera áudio para WhatsApp
                model="gpt" if is_audio_message else None  # Usa GPT para respostas a mensagens de áudio
            )
            
            # Extrai a resposta
            response_text = result.get("text", "")
            
            # Logs da resposta gerada
            logger.info(f"Resposta gerada pelo modelo {result.get('model')}")
            logger.info(f"Resposta: {response_text[:100]}...")
            
            # Envio da resposta de texto
            await send_whatsapp_message(phone, response_text)
            
            # Se tiver áudio, envia o áudio também
            audio_data = result.get("audio", {}).get("data")
            if audio_data:
                logger.info("Enviando áudio para o WhatsApp")
                await send_whatsapp_audio(phone, audio_data)
                
            # Envia para webhook do Make
            await send_to_make(
                phone=phone, 
                message=response_text, 
                original_message=message.text, 
                model=result.get("model"),
                is_audio=is_audio_message
            )
            
            return {
                "status": "success", 
                "response": {
                    "text": response_text,
                    "has_audio": audio_data is not None,
                    "model": result.get("model"),
                    "from_cache": result.get("from_cache", False),
                    "original_message_type": "audio" if is_audio_message else "text"
                }
            }

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            # Em caso de erro, tenta enviar uma mensagem de erro para o usuário
            try:
                error_message = "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?"
                await send_whatsapp_message(phone, error_message)
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
        url = f"{MEGAAPI_HOST}/rest/instance/status"
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