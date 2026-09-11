import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import GEMINI_MODEL, GOOGLE_API_KEY

def get_llm(api_key: Optional[str] = None, temperature: float = 0.2):
    key = api_key or GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        key = "AIzaSy_placeholder_key"
    
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=key,
        temperature=temperature,
        convert_system_message_to_human=False,
    )
