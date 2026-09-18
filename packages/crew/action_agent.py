from __future__ import annotations

from crewai import Agent, LLM


def build_action_agent() -> Agent:
    """
    Action-oriented TT&T agent.

    Responsibilities:
    - recognize explicit customer action requests
    - support controlled write workflows
    - currently support ticket creation

    Authorization and database writes remain deterministic
    backend operations.
    """

    llm = LLM(
        model="ollama/llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.0,
    )

    return Agent(
        role="TT&T Customer Action Agent",
        goal=(
            "Handle explicit customer action requests safely while "
            "respecting authorization and backend action controls."
        ),
        backstory=(
            "You are responsible for customer-requested actions at TT&T. "
            "You never bypass authorization or invent account IDs, line IDs, "
            "ticket IDs, action results, or permissions. You only handle "
            "actions that the customer explicitly requested. The actual "
            "database operation is performed by trusted backend services."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )