from langchain_nvidia_ai_endpoints import ChatNVIDIA
from config.settings import NVIDIA_API_KEY, LLM_MODEL

def get_llm():
    return ChatNVIDIA(
        api_key=NVIDIA_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        top_p=0.8,
        max_tokens=4096,
    )