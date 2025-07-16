#!/usr/bin/env python3
"""Test script to verify service components work correctly."""

import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_service():
    print("🧪 Testing ASO Agent Service Components...")
    
    # Test 1: Import service
    try:
        from src.service.service import app
        print("✅ FastAPI service imports successfully")
    except Exception as e:
        print(f"❌ FastAPI service import failed: {e}")
        return
    
    # Test 2: Import agent
    try:
        from src.agents.agents import get_agent, get_all_agent_info
        agents = get_all_agent_info()
        print(f"✅ Agent registry works: {len(agents)} agents available")
        for agent in agents:
            print(f"   - {agent.key}: {agent.description}")
    except Exception as e:
        print(f"❌ Agent registry failed: {e}")
        return
    
    # Test 3: Test memory components
    try:
        from src.memory import initialize_database, initialize_store
        print("✅ Memory components import successfully")
        
        async with initialize_database() as saver:
            print("✅ Database checkpointer initializes")
            
        async with initialize_store() as store:
            print("✅ Store initializes")
            
    except Exception as e:
        print(f"❌ Memory initialization failed: {e}")
        return
    
    # Test 4: Test ASO agent
    try:
        agent = get_agent("aso-agent")
        print("✅ ASO agent loads successfully")
        
        # Test a simple invocation
        test_input = {
            "messages": [],
        }
        test_config = {
            "configurable": {
                "model": "gpt-4o-mini",
                "market_threshold": 50000,
                "keywords_per_idea": 5
            }
        }
        
        print("🔄 Testing agent invocation...")
        result = await agent.ainvoke(test_input, test_config)
        print("✅ Agent invocation works")
        
    except Exception as e:
        print(f"❌ ASO agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🎉 All tests passed! Service should work correctly.")

if __name__ == "__main__":
    asyncio.run(test_service())