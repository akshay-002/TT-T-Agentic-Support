from __future__ import annotations

from crewai import Crew, Process, Task

from packages.crew.support_agent import (
    build_support_agent,
)

from packages.crew.action_agent import (
    build_action_agent,
)

from packages.router.support_router import (
    route_question,
)

from packages.security.session_context import (
    resolve_session,
)

from packages.security.authorization import (
    authorize_question_resources,
)

from packages.support_service import (
    answer_customer_question_details,
)


async def run_support_flow(
    question: str,
    session_id: str,
    request_id: str | None = None,
) -> dict:
    """
    Main CrewAI orchestration entry point.

    Flow:

        customer
        -> session
        -> authorization
        -> routing
        -> CrewAI agent
        -> MCP/RAG backend
        -> answer + sources
    """

    # ========================================================
    # 1. SESSION
    # ========================================================

    context = resolve_session(
        session_id
    )

    # ========================================================
    # 2. AUTHORIZATION
    # ========================================================

    try:
        authorize_question_resources(
            context=context,
            question=question,
        )

    except PermissionError:
        return {
            "route": "blocked",
            "agent": "security_gate",
            "answer": (
                "I can only access account and line information "
                "associated with your current session."
            ),
            "sources": [],
        }

    # ========================================================
    # 3. ROUTE
    # ========================================================

    route = route_question(
        question
    )

    # ========================================================
    # 4. ACTION AGENT
    # ========================================================

    if route == "support_ticket":

        agent = build_action_agent()

        task = Task(
            description=(
                "Review the TT&T customer request below.\n\n"
                "Confirm that this is an explicit request for a "
                "customer-service action.\n\n"
                "Do not execute database operations yourself.\n"
                "Do not invent account IDs, line IDs, ticket IDs, "
                "permissions, or action results.\n\n"
                f"Customer request:\n{question}"
            ),
            expected_output=(
                "A short internal assessment confirming that "
                "the request belongs to the action workflow."
            ),
            agent=agent,
        )

        crew = Crew(
            agents=[
                agent,
            ],
            tasks=[
                task,
            ],
            process=Process.sequential,
            verbose=False,
        )

        await crew.kickoff_async()

        result = await answer_customer_question_details(
            question=question,
            session_id=session_id,
            request_id=request_id,
        )

        return {
            "route": route,
            "agent": "action_agent",
            "answer": result["answer"],
            "sources": result.get(
                "sources",
                [],
            ),
        }

    # ========================================================
    # 5. SUPPORT RESOLUTION AGENT
    # ========================================================

    agent = build_support_agent()

    task = Task(
        description=(
            "Review the TT&T customer-support request below.\n\n"
            "Identify what kind of TT&T support information "
            "is required to resolve it.\n\n"
            "Do not invent facts.\n"
            "Do not perform database write actions.\n"
            "Do not invent account IDs, line IDs, policy IDs, "
            "or operational results.\n\n"
            f"Detected route: {route}\n\n"
            f"Customer request:\n{question}"
        ),
        expected_output=(
            "A short internal assessment describing what TT&T "
            "information is needed to resolve the request."
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[
            agent,
        ],
        tasks=[
            task,
        ],
        process=Process.sequential,
        verbose=False,
    )

    await crew.kickoff_async()

    result = await answer_customer_question_details(
        question=question,
        session_id=session_id,
        request_id=request_id,
    )

    return {
        "route": route,
        "agent": "support_agent",
        "answer": result["answer"],
        "sources": result.get(
            "sources",
            [],
        ),
    }