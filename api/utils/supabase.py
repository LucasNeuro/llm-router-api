from supabase import create_client, Client
import os
from typing import Dict, Any
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_KEY precisam estar configuradas")

logger.info(f"Inicializando cliente Supabase com URL: {SUPABASE_URL}")

# Inicializa o cliente do Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Cliente Supabase inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar Supabase: {str(e)}")
    logger.error("Verifique se as credenciais estão corretas e se o serviço está disponível")
    logger.exception("Stacktrace completo:")
    raise e

async def save_llm_data(
    prompt: str,
    response: str,
    model: str,
    success: bool,
    confidence: float,
    scores: Dict[str, float],
    indicators: Dict[str, bool],
    cost_analysis: Dict[str, Any],
    request_id: str
) -> None:
    """
    Salva os dados da requisição LLM no Supabase
    """
    try:
        logger.info(f"Iniciando salvamento de dados no Supabase para request_id: {request_id}")
        
        # Extrai informações de custo e tokens
        tokens = cost_analysis.get("tokens", {})
        costs = cost_analysis.get("costs", {})
        usd_costs = costs.get("usd", {})
        brl_costs = costs.get("brl", {})

        data = {
            "prompt": prompt,
            "resposta": response,
            "modelo": model,
            "sucesso": success,
            "confianca": confidence if confidence else 0.0,
            "pontuacao_gpt": scores.get("gpt", 0.0),
            "pontuacao_deepseek": scores.get("deepseek", 0.0),
            "pontuacao_mistral": scores.get("mistral", 0.0),
            "pontuacao_gemini": scores.get("gemini", 0.0),
            "eh_tecnico": indicators.get("technical", False),
            "eh_complexo": indicators.get("complex", False),
            "eh_analitico": indicators.get("analytical", False),
            "eh_simples": indicators.get("simple", False),
            "eh_criativo": indicators.get("creative", False),
            "eh_pratico": indicators.get("practical", False),
            "eh_educacional": indicators.get("educational", False),
            "eh_conversacional": indicators.get("conversational", False),
            "data_criacao": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "cost_analysis": cost_analysis,
            "custo_total_usd": float(usd_costs.get("dollars", 0)),
            "custo_total_brl": float(brl_costs.get("dollars", 0)),
            "custo_total_centavos": int(usd_costs.get("cents", 0)),
            "tokens_prompt": int(tokens.get("prompt", 0)),
            "tokens_resposta": int(tokens.get("completion", 0)),
            "tokens_total": int(tokens.get("total", 0))
        }
        
        logger.info(f"Dados preparados para envio: {json.dumps(data, indent=2, default=str)}")
        
        try:
            logger.info("Enviando dados para tabela llm_router no Supabase...")
            result = supabase.table("llm_router").insert(data).execute()
            logger.info(f"Dados salvos com sucesso: {json.dumps(result.data, indent=2, default=str)}")
            return result
        except Exception as insert_error:
            logger.error(f"Erro ao inserir no Supabase: {str(insert_error)}")
            logger.exception("Stacktrace do erro de inserção:")
            
            # Tenta verificar se a tabela existe
            try:
                logger.info("Verificando se a tabela llm_router existe...")
                test_query = supabase.table("llm_router").select("id").limit(1).execute()
                logger.info(f"Tabela llm_router existe, resultado: {test_query.data}")
            except Exception as table_error:
                logger.error(f"Erro ao verificar tabela: {str(table_error)}")
                
            return None
        
    except Exception as e:
        logger.error(f"Erro geral ao salvar dados no Supabase: {str(e)}")
        logger.exception("Stacktrace completo:")
        return None