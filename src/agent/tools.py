from langchain_core.tools import tool
from lib.appstore import AppstoreApp, search_app_store as _search_app_store
    


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