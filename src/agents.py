from pydantic import BaseModel
from typing import Optional

class AIAgent(BaseModel):
    id: str
    name: str
    specialty: str
    avatar: str  # Stores any emoji string character
    system_prompt: str
    custom_api_key: Optional[str] = None
    model_name: str = "accounts/fireworks/models/llama-v3p1-70b-instruct" # Flexible default
