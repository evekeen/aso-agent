from typing import List
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class KeywordList(BaseModel):
    """List of ASO keywords"""
    keywords: List[str] = Field(description="List of long-tail keywords for App Store optimization")


def generate_keywords(ideas: dict, keywords_len: int) -> list[str]:
    if not ideas:
        raise ValueError("No app ideas provided for keyword generation.")
    
    print(f"Processing {len(ideas)} app ideas for keyword generation...")
    
    try:
        llm = ChatOpenAI(model='gpt-4o-mini').with_structured_output(KeywordList)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize OpenAI LLM: {e}")
    
    keywords = {}
    failed_ideas = []
    
    for idea in ideas:
        prompt = f"""
            You are an App Store SEO specialist helping developers and marketers optimize app visibility.

            Generate exactly {keywords_len} long-tail keywords for the following mobile app idea: {idea}

            - Use long-tail keyword phrases (2–4 words) that are specific and highly relevant.
            - Ensure each keyword reflects the app’s main functionality or user benefit (e.g., stress relief, time-saving, motivation).
            - Include user intent—what a user might search for when looking for this type of app.
            - Prioritize keywords that are competitive for Apple App Store (i.e., low difficulty, solid search volume).
            - Format the output as a numbered list.

            Example:
            App Idea: A meditation app for busy professionals  
            Output:
            1. guided meditation for stress  
            2. quick mindfulness sessions  
            3. meditation app for work stress  
            4. short daily breathing exercises  
            5. stress relief for professionals
        """
        
        try:
            response = llm.invoke(prompt)
            
            if not response.keywords or len(response.keywords) != keywords_len:
                raise ValueError(f"LLM returned invalid keywords for '{idea}': expected {keywords_len} keywords, got {len(response.keywords) if response.keywords else 0}")

            for keyword in response.keywords:
                if not keyword or not isinstance(keyword, str) or len(keyword.strip()) == 0:
                    raise ValueError(f"Invalid keyword generated for '{idea}': empty or non-string keyword")

            keywords[idea] = response.keywords
            print(f"Generated keywords for '{idea}': {response.keywords}")
            
        except Exception as e:
            failed_ideas.append(idea)
            print(f"Failed to generate keywords for '{idea}': {e}")
    if len(failed_ideas) == len(ideas):
        raise RuntimeError(f"Failed to generate keywords for all {len(ideas)} app ideas. No keywords were generated.")
    return keywords