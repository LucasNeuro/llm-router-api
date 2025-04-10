from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
import json
import uuid
from datetime import datetime
from ..utils.logger import logger
from ..utils.agent_service import agent_service
from ..utils.conversation_memory import conversation_manager
from ..llm_router.cost_analyzer import analyze_cost
from ..utils.supabase import save_llm_data
from api.routers.whatsapp import WhatsAppMessage, send_whatsapp_message, send_to_make, cleanup_sessions

router = APIRouter()

@router.post("/agent/{agent_id}/webhook")
async def agent_whatsapp_webhook(
    agent_id: str,
    request: Request, 
    background_tasks: BackgroundTasks
):
    """
    Webhook para receber mensagens do WhatsApp e processá-las com um agente específico
    """
    try:
        # Adiciona tarefa de limpeza em background
        background_tasks.add_task(cleanup_sessions, background_tasks)
        
        # Log do corpo da requisição bruto
        body = await request.body()
        logger.info(f"[Agent {agent_id}] Corpo da requisição bruto: {body.decode()}")

        # Tenta fazer o parse do JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"[Agent {agent_id}] Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Corpo da requisição que causou erro: {body.decode()}")
            return {"status": "error", "reason": "invalid_json"}

        logger.info(f"[Agent {agent_id}] Webhook recebido: {json.dumps(payload, indent=2)}")

        # Verifica se é uma mensagem válida
        if not isinstance(payload, dict):
            logger.error(f"[Agent {agent_id}] Payload inválido, não é um dicionário: {payload}")
            return {"status": "error", "reason": "invalid_payload"}

        # Verifica se é uma mensagem de texto e não é um ACK
        if payload.get("messageType") == "message.ack":
            logger.info(f"[Agent {agent_id}] É uma mensagem de confirmação (ACK), ignorando")
            return {"status": "ignored", "reason": "ack_message"}

        # Verifica se tem a mensagem
        if not payload.get("message"):
            logger.info(f"[Agent {agent_id}] Não é uma mensagem de texto, ignorando")
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
            logger.info(f"[Agent {agent_id}] Tentando encontrar mensagem em estrutura diferente do esperado")
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, str) and len(value) > 0 and len(value) < 500:
                        logger.info(f"Possível mensagem encontrada em campo '{key}': {value}")
                        if not message_text:  # Só atribui se ainda não tiver encontrado
                            message_text = value
        
        # Se não houver mensagem de texto, ignora
        if not message_text:
            logger.info(f"[Agent {agent_id}] Mensagem sem texto extraível: {json.dumps(message_data, indent=2)}")
            return {"status": "ignored", "reason": "no_text_content"}

        # Log da mensagem extraída
        logger.info(f"[Agent {agent_id}] Mensagem extraída com sucesso: {message_text}")

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
                logger.error(f"[Agent {agent_id}] Não foi possível extrair o número do telefone")
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
            logger.info(f"[Agent {agent_id}] Número do remetente: {phone}")

            # Salva a mensagem do usuário na memória
            await conversation_manager.add_message(
                sender_phone=phone,
                role="user",
                content=message_text
            )
            
        except Exception as e:
            logger.error(f"[Agent {agent_id}] Erro ao extrair informações da mensagem: {str(e)}")
            return {"status": "error", "reason": "invalid_message_format"}

        # Processa a mensagem com o Agente
        try:
            logger.info(f"[Agent {agent_id}] Iniciando processamento do agente para mensagem: {message.text}")
            
            # Gera ID único para a requisição
            request_id = str(uuid.uuid4())
            
            # Processa com o agente
            result = await agent_service.process_message(
                agent_id=agent_id,
                message=message_text,
                sender_phone=message.phone
            )
            
            logger.info(f"[Agent {agent_id}] Resposta do agente: {json.dumps(result, indent=2)}")

            # Salva a resposta do assistente na memória
            await conversation_manager.add_message(
                sender_phone=message.phone,
                role="assistant",
                content=result["text"],
                model_used=result["model"]
            )

            # Analisa custos
            cost_analysis = analyze_cost(result["model"], message_text, result["text"])

            # Salva dados no Supabase com tag do agente
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

            # Se precisar de intervenção humana
            handoff_status = "required" if result.get("need_human", False) else "not_required"

            return {
                "status": "success",
                "messageId": message.messageId,
                "agent_id": agent_id,
                "agent_name": result.get("agent_name"),
                "model": result["model"],
                "human_handoff": handoff_status
            }

        except Exception as e:
            logger.error(f"[Agent {agent_id}] Erro ao processar mensagem: {str(e)}")
            # Em caso de erro, tenta enviar uma mensagem de erro para o usuário
            try:
                error_message = "Desculpe, tive um problema ao processar sua mensagem. Por favor, tente novamente mais tarde ou fale com um de nossos atendentes."
                await send_whatsapp_message(message.phone, error_message)
            except:
                pass
            return {"status": "error", "reason": str(e)}

    except Exception as e:
        logger.error(f"[Agent {agent_id}] Erro no webhook: {str(e)}")
        return {"status": "error", "reason": str(e)}

@router.get("/agents")
async def list_agents():
    """Lista todos os agentes disponíveis no sistema"""
    try:
        agents_list = []
        for agent_id, agent in agent_service.agents.items():
            agents_list.append({
                "id": agent_id,
                "name": agent.config.name,
                "gender": agent.config.gender,
                "description": agent.knowledge.company_info.get("nome", "")
            })
        
        return {
            "status": "success",
            "agents": agents_list
        }
    
    except Exception as e:
        logger.error(f"Erro ao listar agentes: {str(e)}")
        return {"status": "error", "reason": str(e)} 