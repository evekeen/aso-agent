"""Agent registry for ASO Agent Service."""

from dataclasses import dataclass
from typing import Dict
from src.agents.aso_agent import aso_agent
from src.schema.schema import AgentInfo


@dataclass
class Agent:
    description: str
    graph: any


# Registry of available agents
agents: Dict[str, Agent] = {
    "aso-agent": Agent(
        description="ASO (App Store Optimization) analysis agent that analyzes app ideas, generates keywords, calculates market sizes, and provides difficulty analysis.",
        graph=aso_agent
    )
}


def get_agent(agent_id: str):
    """Get agent instance by ID."""
    if agent_id not in agents:
        raise ValueError(f"Agent '{agent_id}' not found. Available agents: {list(agents.keys())}")
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    """Get information about all available agents."""
    return [
        AgentInfo(key=agent_id, description=agent.description)
        for agent_id, agent in agents.items()
    ]