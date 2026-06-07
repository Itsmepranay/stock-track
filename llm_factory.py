from langchain_openai import ChatOpenAI
from config.settings import XAI_API_KEY, LLM_MODEL


def get_llm():

    return ChatOpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1",
        model=LLM_MODEL,
        temperature=0,
    )