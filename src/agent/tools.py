from typing import List
from langchain_core.tools import tool
from lib.appstore import AppstoreApp, search_app_store as _search_app_store
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class KeywordList(BaseModel):
    """List of ASO keywords"""
    keywords: List[str] = Field(description="List of 5 long-tail keywords for App Store optimization")


@tool
def generate_initial_keywords(idea: str) -> list[str]:
    """Generate initial ASO keywords for an app idea.
    
    Args:
        idea: The app idea or concept to generate keywords for
        
    Returns:
        A list of 5 long-tail keywords optimized for App Store search
    """
    llm = ChatOpenAI(model='gpt-4o-mini').with_structured_output(KeywordList)
    
    prompt = f"""You are a professional ASO specialist to optimize apps on the Apple AppStore. 
    Generate exactly 5 long-tail keywords for the idea: {idea}
    
    Focus on keywords that:
    - Are specific and long-tail (2-3 words)
    - Target the app's main functionality
    - Include relevant user intent
    - Are competitive for App Store search
    """
    
    response = llm.invoke(prompt)
    return response.keywords
    


async def get_app_keywords(app_ids: list[str]) -> dict[str, list[str]]:
    pass


@tool
async def search_app_store(query: str, limit: int) -> list[AppstoreApp]:
    """Search the App Store for apps matching the query.
    
    Args:
        query: The search term to look for apps
        limit: Maximum number of results to return
        
    Returns:
        A list of AppstoreApp objects with detailed app information
    """
    return await _search_app_store(query, num=limit)