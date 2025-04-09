from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta
from loguru import logger
from .supabase import supabase
import re

class CacheManager:
    """Gerenciador de cache usando Supabase"""
    
    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        """Normaliza o prompt para busca"""
        # Remove pontuação e converte para minúsculas
        normalized = prompt.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        return normalized

    @staticmethod
    def _calculate_similarity(prompt1: str, prompt2: str) -> float:
        """Calcula similaridade entre prompts"""
        words1 = set(CacheManager._normalize_prompt(prompt1).split())
        words2 = set(CacheManager._normalize_prompt(prompt2).split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)

    @staticmethod
    def _ensure_cache_table():
        """Garante que a tabela de cache existe"""
        try:
            # Verifica se a tabela existe
            supabase.table('response_cache').select('id').limit(1).execute()
            logger.info("Tabela de cache verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela de cache: {str(e)}")
            raise

    @staticmethod
    async def get_cached_response(prompt: str) -> Optional[Dict[str, Any]]:
        """Busca uma resposta no cache"""
        try:
            # Primeiro tenta encontrar match exato
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            response = supabase.table('response_cache').select('*').eq('prompt_hash', prompt_hash).execute()
            
            if not (response and response.data and len(response.data) > 0):
                # Se não encontrou match exato, busca todas as entradas não expiradas
                response = supabase.table('response_cache').select('*').gt('expires_at', datetime.utcnow().isoformat()).execute()
                
                if response and response.data:
                    # Procura por prompts similares
                    best_match = None
                    best_similarity = 0.0
                    
                    for entry in response.data:
                        similarity = CacheManager._calculate_similarity(prompt, entry['prompt'])
                        if similarity > 0.8 and similarity > best_similarity:  # 80% de similaridade mínima
                            best_similarity = similarity
                            best_match = entry
                    
                    if best_match:
                        logger.info(f"Cache hit (similaridade: {best_similarity:.2%}) para prompt: {best_match['prompt']}")
                        cached_data = best_match
                    else:
                        return None
                else:
                    return None
            else:
                logger.info(f"Cache hit exato para prompt_hash: {prompt_hash}")
                cached_data = response.data[0]
            
            # Atualiza hit_count e last_accessed
            supabase.table('response_cache').update({
                'hit_count': cached_data['hit_count'] + 1,
                'last_accessed': datetime.utcnow().isoformat()
            }).eq('id', cached_data['id']).execute()
            
            # Processa a resposta do cache
            try:
                cached_response = cached_data['response']
                if isinstance(cached_response, str):
                    cached_response = json.loads(cached_response)
                
                return {
                    "text": cached_response.get("text", ""),
                    "model": cached_data['model'],
                    "success": True,
                    "from_cache": True,
                    "confidence": 1.0,
                    "model_scores": None,
                    "indicators": None,
                    "cache_similarity": best_similarity if 'best_similarity' in locals() else 1.0
                }
            except Exception as e:
                logger.error(f"Erro ao processar resposta do cache: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar cache: {str(e)}")
            return None

    @staticmethod
    async def cache_response(
        prompt: str, 
        response: Dict[str, Any],
        model: str,
        ttl_hours: int = 24
    ) -> bool:
        """Salva uma resposta no cache"""
        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()
            
            # Prepara a resposta para cache
            response_to_cache = {
                "text": response.get("text", ""),
                "model": model,
                "success": response.get("success", True)
            }
            
            # Insere ou atualiza o cache
            data = {
                'prompt_hash': prompt_hash,
                'prompt': prompt,
                'response': response_to_cache,  # Supabase já lida com JSON
                'model': model,
                'expires_at': expires_at,
                'last_accessed': datetime.utcnow().isoformat(),
                'hit_count': 1
            }
            
            supabase.table('response_cache').upsert(data).execute()
            logger.info(f"Resposta cacheada com sucesso: {prompt_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {str(e)}")
            return False

    @staticmethod
    async def cleanup_expired_cache() -> int:
        """Remove entradas expiradas do cache"""
        try:
            response = supabase.table('response_cache').delete().lt('expires_at', datetime.utcnow().isoformat()).execute()
            
            count = len(response.data) if response and response.data else 0
            logger.info(f"Limpeza de cache: {count} entradas removidas")
            return count
            
        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {str(e)}")
            return 0

# Instância global do gerenciador
cache_manager = CacheManager() 