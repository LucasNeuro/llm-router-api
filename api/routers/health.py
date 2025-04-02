from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Endpoint para verificar a saúde da aplicação
    """
    return {"status": "healthy", "message": "LLM Router is running"}