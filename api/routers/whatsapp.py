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
        
        # Garante que a URL base tem o protocolo correto
        base_url = MEGAAPI_BASE_URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
            
        url = f"{base_url}/rest/sendMessage/megabusiness-MoYuzQehcPQ/text"
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

async def send_typing_indicator(phone: str, duration: int = 3):
    """
    Envia indicador de digitação via MegaAPI
    """
    try:
        url = f"{MEGAAPI_BASE_URL}/rest/sendMessage/megabusiness-MoYuzQehcPQ/typing"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
        }
        payload = {
            "messageData": {
                "to": phone,
                "duration": duration
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Erro ao enviar indicador de digitação: {str(e)}")
        return None

async def send_interactive_message(phone: str, message_type: str, content: dict):
    """
    Envia mensagem interativa via MegaAPI
    """
    try:
        url = f"{MEGAAPI_BASE_URL}/rest/sendMessage/megabusiness-MoYuzQehcPQ/{message_type}"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
        }
        payload = {
            "messageData": {
                "to": phone,
                **content
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem interativa: {str(e)}")
        return None

async def send_button_message(phone: str, text: str, buttons: list):
    """
    Envia mensagem com botões via MegaAPI
    """
    return await send_interactive_message(phone, "button", {
        "text": text,
        "buttons": buttons
    })

async def send_list_message(phone: str, text: str, sections: list):
    """
    Envia mensagem com lista via MegaAPI
    """
    return await send_interactive_message(phone, "list", {
        "text": text,
        "sections": sections
    })

async def send_image_message(phone: str, image_url: str, caption: str = None):
    """
    Envia mensagem com imagem via MegaAPI
    """
    return await send_interactive_message(phone, "image", {
        "url": image_url,
        "caption": caption
    })

async def send_location_message(phone: str, latitude: float, longitude: float, name: str = None):
    """
    Envia mensagem com localização via MegaAPI
    """
    return await send_interactive_message(phone, "location", {
        "latitude": latitude,
        "longitude": longitude,
        "name": name
    })

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
        if not payload.get("message"):
            logger.info("Não é uma mensagem de texto, ignorando")
            return {"status": "ignored", "reason": "not_text_message"}

        # Extrai a mensagem do campo correto
        message_text = None
        message_data = payload.get("message", {})
        
        # Tenta extrair a mensagem de diferentes formatos possíveis
        if isinstance(message_data, dict):
            # Formato padrão da MegaAPI
            if "extendedTextMessage" in message_data:
                message_text = message_data["extendedTextMessage"].get("text", "")
            elif "conversation" in message_data:
                message_text = message_data["conversation"]
            elif "text" in message_data:
                if isinstance(message_data["text"], dict):
                    message_text = message_data["text"].get("message", "")
                else:
                    message_text = message_data["text"]
            # Verifica formato alternativo
            elif "body" in message_data:
                message_text = message_data["body"]
        # Formato alternativo onde a mensagem está diretamente no payload
        elif "text" in payload:
            message_text = payload["text"]
        elif "body" in payload:
            message_text = payload["body"]
        
        # Se ainda não encontrou, tenta procurar em qualquer lugar no payload
        if not message_text:
            logger.info("Tentando encontrar mensagem em estrutura diferente do esperado")
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, str) and len(value) > 0 and len(value) < 500:
                        logger.info(f"Possível mensagem encontrada em campo '{key}': {value}")
                        if not message_text:  # Só atribui se ainda não tiver encontrado
                            message_text = value
        
        # Se não houver mensagem de texto, ignora
        if not message_text:
            logger.info(f"Mensagem sem texto extraível: {json.dumps(message_data, indent=2)}")
            return {"status": "ignored", "reason": "no_text_content"}

        # Log da mensagem extraída
        logger.info(f"Mensagem extraída com sucesso: {message_text}")

        # Extrai informações da mensagem
        try:
            # Tenta extrair o número do remetente de diferentes lugares
            phone = None
            
            # Formato padrão - do remoteJid
            if "key" in payload and "remoteJid" in payload["key"]:
                remote_jid = payload["key"]["remoteJid"]
                if "@" in remote_jid:
                    phone = remote_jid.split("@")[0]
            
            # Formato alternativo - diretamente no campo 'from'
            if not phone and "from" in payload:
                phone = payload["from"]
                # Remove @c.us ou @s.whatsapp.net se existir
                if phone and "@" in phone:
                    phone = phone.split("@")[0]
            
            # Formato alternativo - no campo sender
            if not phone and "sender" in payload:
                phone = payload["sender"]
            
            # Se ainda não encontrou, procura em qualquer lugar no payload
            if not phone:
                if isinstance(payload, dict):
                    for key in ["phone", "sender_id", "customer", "number"]:
                        if key in payload and isinstance(payload[key], str):
                            phone = payload[key]
                            break
                            
            if not phone:
                logger.error("Não foi possível extrair o número do telefone")
                return {"status": "error", "reason": "no_phone_number"}
                
            # Limpa o número de telefone
            phone = str(phone).replace("+", "")
            # Remove o prefixo "55" se existir
            if phone.startswith("55") and len(phone) > 10:
                phone = phone[2:]
                
            message = WhatsAppMessage(
                messageType=payload.get("messageType", "text"),
                text=message_text,
                phone=phone,
                instanceId=payload.get("instance_key", ""),
                messageId=payload.get("key", {}).get("id", ""),
                timestamp=payload.get("messageTimestamp", 0)
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
            
            # Envia indicador de digitação
            await send_typing_indicator(message.phone)
            
            # Força resposta em português do Brasil
            prompt_ptbr = f"""Por favor, responda em português do Brasil de forma natural e coloquial:

{message.text}

Lembre-se: Sua resposta DEVE ser em português do Brasil."""

            # Usa o LLM Router com contexto da conversa
            result = await llm_router.route_prompt(
                prompt=prompt_ptbr,
                sender_phone=message.phone
            )
            
            logger.info(f"Resposta do LLM Router: {json.dumps(result, indent=2)}")

            # Verifica se a resposta requer interação
            if "planos" in message.text.lower() or "preços" in message.text.lower():
                # Envia lista de planos
                sections = [
                    {
                        "title": "Planos Básicos",
                        "rows": [
                            {
                                "id": "basic_100",
                                "title": "100 Mega",
                                "description": "Ideal para uso básico"
                            },
                            {
                                "id": "basic_200",
                                "title": "200 Mega",
                                "description": "Bom para streaming"
                            }
                        ]
                    }
                ]
                await send_list_message(message.phone, "Confira nossos planos disponíveis:", sections)
            
            elif "cobertura" in message.text.lower() or "área" in message.text.lower():
                # Envia localização da empresa
                await send_location_message(
                    message.phone,
                    latitude=-23.550520,
                    longitude=-46.633308,
                    name="G4 TELECOM - Matriz"
                )
                # Envia imagem do mapa de cobertura
                await send_image_message(
                    message.phone,
                    image_url="URL_DO_MAPA_DE_COBERTURA",
                    caption="Mapa de cobertura da G4 TELECOM"
                )

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
        # Garante que a URL base tem o protocolo correto
        base_url = MEGAAPI_BASE_URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
            
        url = f"{base_url}/rest/instance/status"
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MEGAAPI_API_KEY}"
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