from typing import Dict, Any, Optional
from api.neo4j.connector import get_db
from api.utils.logger import logger
import json
from datetime import datetime

async def save_to_cache(
    prompt: str,
    response: Dict[str, Any],
    model: str,
    task_type: Optional[str] = None
) -> bool:
    """
    Salva a resposta no cache do Neo4j
    
    Args:
        prompt: Mensagem original
        response: Resposta do modelo
        model: Nome do modelo usado
        task_type: Tipo de tarefa (opcional)
    """
    try:
        db = get_db()
        
        # Cria query para salvar resposta
        query = """
        MERGE (p:Prompt {text: $prompt})
        CREATE (r:Response {
            text: $response_text,
            model: $model,
            task_type: $task_type,
            timestamp: $timestamp,
            tokens: $tokens
        })
        CREATE (p)-[:HAS_RESPONSE]->(r)
        """
        
        params = {
            "prompt": prompt,
            "response_text": response["text"],
            "model": model,
            "task_type": task_type or "unknown",
            "timestamp": datetime.now().isoformat(),
            "tokens": response.get("tokens")
        }
        
        db.execute_query(query, params)
        logger.info(f"Resposta salva no cache para prompt: {prompt[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar no cache: {str(e)}")
        return False

async def get_from_cache(prompt: str, task_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Busca resposta similar no cache
    
    Args:
        prompt: Mensagem do usuário
        task_type: Tipo de tarefa (opcional)
    """
    try:
        db = get_db()
        
        # Query para buscar resposta similar
        query = """
        MATCH (p:Prompt)-[:HAS_RESPONSE]->(r:Response)
        WHERE p.text CONTAINS $prompt_part
        AND (r.task_type = $task_type OR $task_type IS NULL)
        RETURN r
        ORDER BY r.timestamp DESC
        LIMIT 1
        """
        
        # Usa parte significativa do prompt para busca
        prompt_part = " ".join(prompt.split()[:5])  # Primeiras 5 palavras
        
        params = {
            "prompt_part": prompt_part,
            "task_type": task_type
        }
        
        result = db.execute_query(query, params)
        
        if result and len(result) > 0:
            response = result[0]["r"]
            logger.info(f"Resposta encontrada no cache para prompt similar: {prompt_part}")
            return {
                "text": response["text"],
                "model": response["model"],
                "tokens": response.get("tokens"),
                "cached": True,
                "success": True
            }
            
        return None
        
    except Exception as e:
        logger.error(f"Erro ao buscar do cache: {str(e)}")
        return None 