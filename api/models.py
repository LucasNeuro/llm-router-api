from pydantic import BaseModel
from typing import Optional


class WhatsAppMessage(BaseModel):
    messageType: str
    text: Optional[str] = None
    phone: str
    instanceId: str
    messageId: str
    timestamp: Optional[int] = None
