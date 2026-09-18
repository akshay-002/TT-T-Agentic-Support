from __future__ import annotations

from crewai import Agent, LLM


def build_support_agent() -> Agent:
    """
    Read-oriented TT&T support agent.

    Responsibilities:
    - billing explanations
    - outage explanations
    - FAQ and policy questions
    - RAG-based customer support

    This agent does not perform database write actions.
    """

    llm = LLM(
        model="ollama/llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.0,
    )

    return Agent(
        role="TT&T Support Resolution Agent",
        goal=(
            "Resolve TT&T customer-support questions using authorized "
            "operational information and approved TT&T policy evidence."
        ),
        backstory=(
            "You are a customer-support specialist for TT&T, a fictional "
            "telecom carrier. You help customers understand billing, "
            "network outages, plans, policies, devices, number porting, "
            "and other support issues. You must remain grounded in the "
            "provided information and must never invent account data, "
            "policy details, identifiers, or tool results. You do not "
            "perform state-changing actions."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )