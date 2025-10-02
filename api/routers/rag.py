from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from loguru import logger
from api.utils.rag import index_documents, search_similar


router = APIRouter()


class RAGDocument(BaseModel):
    id: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None
    namespace: Optional[str] = None


class RAGIndexRequest(BaseModel):
    documents: List[RAGDocument]
    namespace: Optional[str] = None


@router.post("/rag/index")
async def rag_index(req: RAGIndexRequest):
    try:
        payload = [doc.model_dump() for doc in req.documents]
        result = await index_documents(payload, namespace=req.namespace)
        return {"status": "ok", "indexed": result.get("inserted", 0)}
    except Exception as e:
        logger.error(f"Erro no index do RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/search")
async def rag_search(q: str = Query(..., min_length=2), top_k: int = 5, namespace: Optional[str] = None):
    try:
        results = await search_similar(q, top_k=top_k, namespace=namespace)
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"Erro na busca do RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

