from typing import List, Dict, Any, Optional, Tuple
import os
import math
from datetime import datetime
from openai import OpenAI
from loguru import logger
from .supabase import supabase


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("GPT_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("GPT_API_KEY/OPENAI_API_KEY não configurada para embeddings")
    return OpenAI(api_key=api_key)


def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    if len(vector_a) != len(vector_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


async def embed_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    client = _get_openai_client()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


async def index_documents(documents: List[Dict[str, Any]], namespace: Optional[str] = None) -> Dict[str, Any]:
    contents = [doc.get("content", "") for doc in documents]
    embeddings = await embed_texts(contents)

    rows = []
    for idx, doc in enumerate(documents):
        row = {
            "id": doc.get("id"),
            "content": contents[idx],
            "metadata": doc.get("metadata", {}),
            "embedding": embeddings[idx],
            "namespace": namespace or doc.get("namespace"),
            "created_at": datetime.utcnow().isoformat()
        }
        rows.append(row)

    try:
        result = supabase.table("rag_documents").upsert(rows).execute()
        return {"inserted": len(rows), "result": result.data}
    except Exception as e:
        logger.error(f"Erro ao indexar documentos no Supabase: {str(e)}")
        raise


async def fetch_candidate_documents(limit: int = 200, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        query = supabase.table("rag_documents").select("id,content,metadata,embedding,namespace,created_at").order("created_at", desc=True).limit(limit)
        if namespace:
            query = query.eq("namespace", namespace)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar documentos candidatos: {str(e)}")
        return []


async def search_similar(query: str, top_k: int = 5, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
    query_embedding = (await embed_texts([query]))[0]
    candidates = await fetch_candidate_documents(namespace=namespace)

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for doc in candidates:
        embedding = doc.get("embedding") or []
        score = _cosine_similarity(query_embedding, embedding)
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: max(0, top_k)]
    return [
        {
            "id": doc.get("id"),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "score": float(score),
            "namespace": doc.get("namespace")
        }
        for score, doc in top
    ]


def format_chunks_as_context(chunks: List[Dict[str, Any]], max_chars: int = 2000) -> str:
    parts: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata") or {}
        title = meta.get("title") or meta.get("source") or f"Doc {idx}"
        snippet = chunk.get("content", "").strip()
        entry = f"[{title}]\n{snippet}"
        parts.append(entry)
        joined = "\n\n".join(parts)
        if len(joined) >= max_chars:
            break
    context_header = (
        "Você recebeu trechos de contexto relevantes abaixo. Use-os para responder com precisão."
    )
    return context_header + "\n\n" + "\n\n".join(parts)

