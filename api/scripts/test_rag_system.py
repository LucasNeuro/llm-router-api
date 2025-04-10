import os
import uuid
import json
import asyncio
from dotenv import load_dotenv
from api.utils.supabase import supabase
from api.utils.bucket_storage import setup_storage_bucket, upload_document_to_bucket
from api.utils.embedding import split_text_into_chunks, create_embeddings_from_chunks

# Carrega variáveis de ambiente
load_dotenv()

async def create_test_agent():
    """Cria um agente de teste para o sistema RAG"""
    print("Criando agente de teste...")
    
    # Dados do agente
    agent_id = str(uuid.uuid4())
    agent_data = {
        "agent_id": agent_id,
        "name": "Agente de Atendimento",
        "description": "Agente de teste para atendimento ao cliente",
        "provider_id": "exemplo",
        "personality": "helpful",
        "tone_of_voice": "friendly",
        "role": "customer_service",
        "search_top_k": 5,
        "similarity_threshold": 0.75,
        "add_citations": True,
        "system_instructions": "Você é um assistente de atendimento ao cliente da Exemplo S.A. Use as informações fornecidas para ajudar os clientes.",
        "preferred_model": None,
        "allowed_categories": ["atendimento", "cobranca", "suporte"],
        "response_format": "text"
    }
    
    try:
        # Inserir na tabela rag_agents
        result = supabase.table("rag_agents").insert(agent_data).execute()
        print(f"✅ Agente criado com sucesso: {agent_id}")
        return agent_id
    except Exception as e:
        print(f"❌ Erro ao criar agente: {str(e)}")
        return None

async def upload_test_document():
    """Faz upload de um documento de teste e processa para o sistema RAG"""
    print("Criando documento de teste...")
    
    # Criar um arquivo de teste
    test_content = """
    MANUAL DE ATENDIMENTO AO CLIENTE - EXEMPLO S.A.
    
    1. INTRODUÇÃO
    Este manual contém diretrizes para atendimento ao cliente da Exemplo S.A.
    
    2. PROTOCOLOS DE ATENDIMENTO
    - Cumprimente o cliente usando "Olá, bem-vindo à Exemplo S.A. Como posso ajudar?"
    - Identifique-se pelo nome
    - Escute atentamente a solicitação do cliente
    
    3. RESOLUÇÃO DE PROBLEMAS
    - Confirme o entendimento do problema
    - Ofereça soluções claras e objetivas
    - O prazo máximo para resolução de problemas é de 48 horas
    
    4. POLÍTICAS DE REEMBOLSO
    Produtos podem ser devolvidos em até 7 dias após a compra mediante apresentação da nota fiscal.
    O reembolso será processado em até 10 dias úteis.
    """
    
    file_path = "documento_teste.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"✅ Documento de teste criado: {file_path}")
    
    # Configurar bucket e fazer upload
    print("Configurando bucket de armazenamento...")
    bucket_name = "provider-documents"
    if not await setup_storage_bucket(bucket_name):
        print("❌ Erro ao configurar bucket")
        return None
    
    # Dados do documento
    document_data = {
        "title": "Manual de Atendimento",
        "category": "atendimento",
        "provider_id": "exemplo",
        "file_name": os.path.basename(file_path),
        "file_path": file_path
    }
    
    # Fazer upload do arquivo
    print("Fazendo upload do documento...")
    document_id = None
    try:
        document_id = await upload_document_to_bucket(file_path, bucket_name, document_data)
        print(f"✅ Upload realizado com sucesso: {document_id}")
    except Exception as e:
        print(f"❌ Erro ao fazer upload: {str(e)}")
        return None
    
    # Processar embeddings
    print("Processando texto em chunks e gerando embeddings...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Dividir em chunks
        chunks = split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200)
        print(f"✅ Texto dividido em {len(chunks)} chunks")
        
        # Gerar embeddings
        await create_embeddings_from_chunks(chunks, document_id)
        print("✅ Embeddings gerados e salvos com sucesso")
        
        return document_id
    except Exception as e:
        print(f"❌ Erro ao processar embeddings: {str(e)}")
        return None

async def query_agent(agent_id, query_text):
    """Consulta um agente RAG"""
    print(f"Consultando agente {agent_id}...")
    
    try:
        # Obter dados do agente
        agent_result = supabase.table("rag_agents").select("*").eq("agent_id", agent_id).execute()
        
        if not agent_result.data:
            print(f"❌ Agente não encontrado: {agent_id}")
            return None
        
        agent = agent_result.data[0]
        search_top_k = agent.get("search_top_k", 5)
        
        # Criar embedding para a consulta
        query_embedding = await create_embeddings_from_chunks([query_text])
        
        if not query_embedding:
            print("❌ Erro ao gerar embedding para a consulta")
            return None
        
        # Buscar documentos relevantes usando similaridade de cosenos
        query = f"""
        SELECT 
            e.content,
            d.title as document_title,
            d.category,
            1 - (e.embedding <=> '{json.dumps(query_embedding[0])}') as similarity
        FROM 
            provider_embeddings e
        JOIN 
            provider_documents d ON e.document_id = d.id
        WHERE 
            d.category = ANY('{json.dumps(agent.get("allowed_categories", ["atendimento"]))}')
        ORDER BY 
            similarity DESC
        LIMIT {search_top_k}
        """
        
        result = supabase.rpc("query_embeddings", {
            "query_embedding": query_embedding[0],
            "match_threshold": agent.get("similarity_threshold", 0.75),
            "match_count": search_top_k
        }).execute()
        
        print(f"✅ Encontrado {len(result.data)} documentos relevantes")
        
        # Mostrar resultados
        for i, doc in enumerate(result.data):
            print(f"\nDocumento {i+1} (Similaridade: {doc.get('similarity', 0):.3f}):")
            print(f"Título: {doc.get('document_title', 'Sem título')}")
            print(f"Trecho: {doc.get('content', '')[:100]}...")
        
        return result.data
    except Exception as e:
        print(f"❌ Erro ao consultar agente: {str(e)}")
        return None

async def main():
    """Função principal para testar o sistema RAG"""
    print("=== TESTE DO SISTEMA RAG ===")
    
    # 1. Criar agente
    agent_id = await create_test_agent()
    if not agent_id:
        print("⚠️ Teste interrompido: falha ao criar agente")
        return
    
    # 2. Fazer upload de documento
    document_id = await upload_test_document()
    if not document_id:
        print("⚠️ Teste interrompido: falha ao processar documento")
        return
    
    # 3. Consultar agente
    print("\n=== TESTE DE CONSULTA ===")
    consulta = "Qual é o prazo para reembolso de produtos?"
    print(f"Consulta: {consulta}")
    
    results = await query_agent(agent_id, consulta)
    
    print("\n=== TESTE CONCLUÍDO ===")
    print(f"✅ Agente ID: {agent_id}")
    print(f"✅ Documento ID: {document_id}")
    
    if results:
        print("✅ Sistema RAG funcionando corretamente!")
    else:
        print("⚠️ Houve problemas na consulta ao sistema RAG.")

if __name__ == "__main__":
    asyncio.run(main())