import os
from dotenv import load_dotenv
import httpx
import json

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL e SUPABASE_KEY devem estar definidos no .env")

def execute_query(query: str) -> dict:
    """Executa uma query SQL via REST API do Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    data = {
        "query": query
    }
    
    response = httpx.post(
        f"{SUPABASE_URL}/rest/v1/rpc/execute",
        headers=headers,
        json=data
    )
    
    return response.json()

def apply_migration():
    try:
        # Lê o arquivo SQL
        with open('api/migrations/apply_migration.sql', 'r') as file:
            sql = file.read()
            
        print("✅ Arquivo SQL carregado")
        print("\nExecutando queries...")
        
        # Divide e executa as queries
        queries = [q.strip() for q in sql.split(';') if q.strip()]
        
        for i, query in enumerate(queries, 1):
            try:
                result = execute_query(query)
                print(f"\n✅ Query {i}/{len(queries)} executada:")
                print(f"{query[:100]}...")
                if isinstance(result, dict) and result.get('error'):
                    print(f"⚠️ Aviso: {result['error']}")
            except Exception as e:
                print(f"\n❌ Erro na query {i}/{len(queries)}:")
                print(f"{query[:100]}...")
                print(f"Erro: {str(e)}")
                
        print("\n✨ Migração concluída!")
        
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {str(e)}")

if __name__ == "__main__":
    apply_migration() 