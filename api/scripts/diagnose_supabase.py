#!/usr/bin/env python
"""
Script para diagnosticar problemas de conexão com o Supabase.
"""

import os
import sys
import importlib
import inspect
import logging
import traceback
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("supabase_diagnóstico")

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

def check_supabase_version():
    """Verifica a versão do pacote supabase instalado"""
    try:
        import supabase
        logger.info(f"Versão do pacote supabase: {supabase.__version__}")
        
        # Verificar se existe create_client
        if hasattr(supabase, 'create_client'):
            logger.info("Função create_client encontrada")
            create_client_params = inspect.signature(supabase.create_client).parameters
            logger.info(f"Parâmetros de create_client: {list(create_client_params.keys())}")
        else:
            logger.error("Função create_client não encontrada!")
        
        # Verificar cliente
        try:
            from supabase._sync.client import SyncClient
            client_params = inspect.signature(SyncClient.__init__).parameters
            logger.info(f"Parâmetros de SyncClient.__init__: {list(client_params.keys())}")
        except ImportError:
            logger.error("Não foi possível importar SyncClient")
            
        # Verificar dependências
        try:
            import gotrue
            logger.info(f"Versão do pacote gotrue: {gotrue.__version__}")
        except (ImportError, AttributeError):
            logger.error("Problema ao verificar pacote gotrue")
            
    except ImportError:
        logger.error("Pacote supabase não encontrado!")
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar versão do supabase: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

def test_supabase_connection():
    """Tenta estabelecer uma conexão com o Supabase"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Configurações do Supabase
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Variáveis de ambiente SUPABASE_URL e SUPABASE_KEY não configuradas")
            return False
            
        logger.info(f"Tentando conectar ao Supabase URL: {SUPABASE_URL}")
        
        # Tentativa 1: create_client padrão
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Conexão com Supabase estabelecida com create_client!")
            
            # Verificar se é possível fazer uma consulta simples
            response = client.table("llm_router").select("id").limit(1).execute()
            logger.info(f"Consulta de teste realizada com sucesso: {response}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar com create_client: {str(e)}")
            if 'proxy' in str(e):
                logger.info("Detectado erro relacionado a proxy, tentando método alternativo...")
            
            # Tentativa 2: SyncClient diretamente
            try:
                from supabase._sync.client import SyncClient
                client = SyncClient(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Conexão com Supabase estabelecida com SyncClient!")
                
                # Verificar se é possível fazer uma consulta simples
                response = client.table("llm_router").select("id").limit(1).execute()
                logger.info(f"Consulta de teste realizada com sucesso: {response}")
                return True
            except Exception as inner_e:
                logger.error(f"Erro ao conectar com SyncClient: {str(inner_e)}")
                traceback.print_exc()
                return False
    
    except Exception as e:
        logger.error(f"Erro ao testar conexão com Supabase: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("=== Iniciando diagnóstico do Supabase ===")
    
    # Verificar versão
    logger.info("Verificando versão do pacote supabase...")
    check_supabase_version()
    
    # Testar conexão
    logger.info("Testando conexão com Supabase...")
    success = test_supabase_connection()
    
    if success:
        logger.info("✅ Diagnóstico completo: Conexão com Supabase estabelecida com sucesso!")
        sys.exit(0)
    else:
        logger.error("❌ Diagnóstico completo: Não foi possível conectar ao Supabase!")
        sys.exit(1)