from supabase import create_client, Client
import os
from typing import Dict, Any
import json
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_KEY precisam estar configuradas")

# Inicializa o cliente do Supabase com configuração mínima
try:
    supabase: Client = create_client(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY
    )
except Exception as e:
    print(f"Erro ao inicializar Supabase: {str(e)}")
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
        
        result = supabase.table("llm_router").insert(data).execute()
        return result
        
    except Exception as e:
        print(f"Erro ao salvar dados no Supabase: {str(e)}")
        return None 