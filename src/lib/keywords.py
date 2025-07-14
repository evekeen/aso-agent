from typing import List
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class KeywordList(BaseModel):
    """List of ASO keywords"""
    two_word: List[str] = Field(description="List of two-word keywords for App Store optimization")
    three_word: List[str] = Field(description="List of long-tail three-word keywords for App Store optimization")


def generate_keywords(ideas: dict, keywords_len: int) -> List[str]:
    if not ideas:
        raise ValueError("No app ideas provided for keyword generation.")
    
    print(f"Processing {len(ideas)} app ideas for keyword generation...")
    
    try:
        llm = ChatOpenAI(model='gpt-4o-mini').with_structured_output(KeywordList)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize OpenAI LLM: {e}")
    
    keywords = {}
    failed_ideas = []
    extended_keywords_len = keywords_len + 3  # Allow for some flexibility in keyword generation
    
    for idea in ideas:
        prompt = f"""
            You are an App Store SEO specialist helping developers and marketers optimize app visibility.

            Generate exactly {extended_keywords_len} long-tail keywords for the following mobile app idea: {idea}

            - Use long-tail keyword phrases (1–3 words) that are specific and highly relevant.
            - Ensure each keyword reflects the app’s main functionality or user benefit (e.g., stress relief, time-saving, motivation).
            - Include user intent—what a user might search for when looking for this type of app.
            - Prioritize keywords that are competitive for Apple App Store (i.e., low difficulty, solid search volume).
            - Format the output as a numbered list.
            
            Make sure to generate:
            - {extended_keywords_len/2} two-word keywords
            - {extended_keywords_len/2} three-word keywords

            Example:
            App Idea: A meditation app for busy professionals  
            Output:
            1. guided meditation
            2. stress relief
            3. quick mindfulness sessions  
            4. meditation for work
        """
        
        try:
            response = llm.invoke(prompt)
            
            all_keywords = response.two_word + response.three_word
            
            if not all_keywords or len(all_keywords) < keywords_len:
                raise ValueError(f"LLM returned invalid keywords for '{idea}': expected {keywords_len} keywords, got {len(all_keywords) if all_keywords else 0}")

            for keyword in all_keywords:
                if not keyword or not isinstance(keyword, str) or len(keyword.strip()) == 0:
                    raise ValueError(f"Invalid keyword generated for '{idea}': empty or non-string keyword")

            keywords[idea] = all_keywords
            print(f"Generated keywords for '{idea}': {all_keywords}")
            
        except Exception as e:
            failed_ideas.append(idea)
            print(f"Failed to generate keywords for '{idea}': {e}")
    if len(failed_ideas) == len(ideas):
        raise RuntimeError(f"Failed to generate keywords for all {len(ideas)} app ideas. No keywords were generated.")
    return keywords


if __name__ == "__main__":
    import asyncio
    
    # Example usage
    ideas = {
        "A meditation app for busy professionals": None,
        "A productivity app for remote teams": None,
        "A fitness tracker for outdoor enthusiasts": None
    }
    
    try:
        keywords = generate_keywords(ideas, keywords_len=20)
        print("Generated keywords:")
        for idea, kws in keywords.items():
            print(f"{idea}: {kws}")
    except Exception as e:
        print(f"Error generating keywords: {e}")