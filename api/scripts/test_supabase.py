import os
from dotenv import load_dotenv
from pathlib import Path
import asyncio
from supabase import create_client, Client
from datetime import datetime, timedelta
import json
from loguru import logger

def print_step(message: str, success: bool = None):
    """Função auxiliar para imprimir passos do teste"""
    if success is None:
        print(f"\n🔄 {message}")
    elif success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

async def test_supabase_connection():
    """Testa a conexão com o Supabase e as operações básicas"""
    try:
        # 1. Carrega variáveis de ambiente
        env_path = Path(__file__).parent.parent.parent / '.env'
        print_step(f"Procurando arquivo .env em: {env_path}")
        
        if not env_path.exists():
            print_step("Arquivo .env não encontrado", False)
            return False
        
        print_step("Arquivo .env encontrado", True)
        load_dotenv(env_path)
        
        # 2. Verifica variáveis do Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print_step("Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas", False)
            return False
            
        print_step(f"SUPABASE_URL encontrada: {supabase_url}", True)
        print_step(f"SUPABASE_KEY encontrada: {supabase_key[:10]}...", True)
        
        # 3. Tenta criar cliente Supabase
        print_step("Inicializando cliente Supabase...")
        supabase = create_client(supabase_url, supabase_key)
        print_step("Cliente Supabase inicializado com sucesso", True)
        
        # 4. Testa tabela response_cache
        print_step("\nTestando tabela response_cache...")
        try:
            # Tenta selecionar um registro
            response = supabase.table('response_cache').select('*').limit(1).execute()
            print_step("Tabela response_cache existe e é acessível", True)
            
            # Tenta inserir um registro de teste
            test_data = {
                "prompt_hash": "test_hash_" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "prompt": "Teste de inserção",
                "response": json.dumps({"text": "Resposta de teste"}),
                "model": "test_model",
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
                "hit_count": 1,
                "last_accessed": datetime.now().isoformat()
            }
            
            response = supabase.table('response_cache').insert(test_data).execute()
            print_step("Inserção na tabela response_cache bem sucedida", True)
            
        except Exception as e:
            print_step(f"Erro ao testar tabela response_cache: {str(e)}", False)
        
        # 5. Testa tabela conversation_memory
        print_step("\nTestando tabela conversation_memory...")
        try:
            # Tenta selecionar um registro
            response = supabase.table('conversation_memory').select('*').limit(1).execute()
            print_step("Tabela conversation_memory existe e é acessível", True)
            
            # Tenta inserir um registro de teste
            test_data = {
                "sender_phone": "5511999999999_" + datetime.now().strftime("%Y%m%d%H%M%S"),  # Adicionado timestamp para evitar conflito de unique
                "conversation_memory": {
                    "messages": [{
                        "role": "user",
                        "content": "Mensagem de teste",
                        "timestamp": datetime.now().isoformat()
                    }]
                },
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            }
            
            response = supabase.table('conversation_memory').insert(test_data).execute()
            print_step("Inserção na tabela conversation_memory bem sucedida", True)
            
        except Exception as e:
            print_step(f"Erro ao testar tabela conversation_memory: {str(e)}", False)
        
        return True
        
    except Exception as e:
        print_step(f"Erro geral: {str(e)}", False)
        return False

if __name__ == "__main__":
    print("\n=== Teste de Conexão com Supabase ===\n")
    success = asyncio.run(test_supabase_connection())
    
    print("\n=== Resultado Final ===")
    if success:
        print("✅ Todos os testes completados!")
        print("\nSugestões:")
        print("1. Verifique os logs acima para garantir que todas as operações foram bem sucedidas")
        print("2. Se alguma operação falhou, corrija o problema e execute o teste novamente")
        print("3. Use o painel do Supabase para verificar se os dados de teste foram inseridos corretamente")
    else:
        print("❌ Teste falhou!")
        print("\nSugestões:")
        print("1. Verifique se as variáveis de ambiente estão configuradas corretamente")
        print("2. Confirme se a URL e a chave do Supabase estão corretas")
        print("3. Verifique se você tem as permissões necessárias no projeto Supabase")