from lib.appstore import AppstoreApp, search_app_store as _search_app_store


def generate_initial_keywords(idea: str) -> list[str]:
    # TODO use LLM call to generate initial keywords
    return ["keyword1", "keyword2", "keyword3"]


async def get_app_keywords(app_ids: list[str]) -> dict[str, list[str]]:
    pass


async def search_app_store(query: str, limit: int) -> list[AppstoreApp]:
    """Search the App Store for apps matching the query.
    
    Args:
        query: Search term
        limit: Maximum number of results to return
        
    Returns:
        List of AppstoreApp objects with app details
    """
    return await _search_app_store(query, num=limit)