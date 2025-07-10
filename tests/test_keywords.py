from src.agent.tools import generate_initial_keywords


def test_generate_keywords():
    print("Testing generate_initial_keywords function...\n")
    
    # Test 1: Fitness app idea
    print("Test 1: Fitness tracking app")
    idea = "fitness tracking app for beginners"
    keywords = generate_initial_keywords.invoke({"idea": idea})
    print(f"Input idea: {idea}")
    print(f"Generated {len(keywords)} keywords:")
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword}")
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert all(isinstance(k, str) and k.strip() for k in keywords)
    print("✓ Test 1 passed\n")   


if __name__ == "__main__":
    test_generate_keywords()