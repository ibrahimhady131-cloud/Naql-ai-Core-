"""Agent Orchestrator API routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from ..agents.naql_brain import AgentContext
from ..memory.vector_store import vector_memory

router = APIRouter(prefix="/api/v1", tags=["agent"])

# Session storage
_sessions: dict[str, list[dict]] = {}


@router.post("/chat")
async def chat(
    user_id: str,
    message: str,
    session_id: str | None = None,
    language: str = "en",
) -> dict:
    """Send a message to the Naql.ai agent and get a response."""
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Initialize session history
    if session_id not in _sessions:
        _sessions[session_id] = []

    # Store user message
    _sessions[session_id].append(
        {
            "role": "user",
            "content": message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    # Create agent context
    context = AgentContext(
        session_id=session_id,
        user_id=user_id,
        user_message=message,
        language=language,
    )

    # Run through the LangGraph pipeline
    # Note: In production, this would use the compiled graph
    # For now, execute steps sequentially
    from ..agents.naql_brain import AgentState, dispatch_step, execute_step, plan_step, respond_step

    context = plan_step(context)

    if context.sub_tasks:
        context = await execute_step(context)

        if context.state == AgentState.DISPATCHING:
            context = dispatch_step(context)

    context = respond_step(context)

    # Store agent response
    _sessions[session_id].append(
        {
            "role": "assistant",
            "content": context.response,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    # Store interaction in vector memory for future RAG
    await vector_memory.store_interaction(
        session_id=session_id,
        user_id=user_id,
        summary=f"User asked about: {context.intent}. Response provided.",
        intent=context.intent,
    )

    return {
        "session_id": session_id,
        "response": context.response,
        "intent": context.intent,
        "actions_taken": context.tool_results,
    }


@router.get("/chat/history/{session_id}")
async def get_conversation_history(session_id: str, limit: int = 50) -> dict:
    """Get conversation history for a session."""
    messages = _sessions.get(session_id, [])
    return {
        "session_id": session_id,
        "messages": messages[-limit:],
        "total": len(messages),
    }


@router.post("/agent/event")
async def process_event(event_type: str, payload: dict) -> dict:
    """Process a real-time event through the Sentinel."""
    from ..agents.naql_brain import sentinel

    result = await sentinel.process_event(event_type, payload)

    return {
        "status": "processed",
        "event_type": event_type,
        "result": result,
    }


@router.post("/agent/trigger")
async def trigger_agent(request: dict) -> dict:
    """Trigger the agent to process a shipment (called by mega_simulator)."""
    shipment_id = request.get("shipment_id")
    pickup_h3 = request.get("pickup_h3", "")
    dropoff_h3 = request.get("dropoff_h3", "")
    cargo_type = request.get("cargo_type", "general")
    
    if not shipment_id:
        return {"status": "error", "message": "shipment_id required"}
    
    try:
        from ..logic.graph import run_agent_for_shipment
        
        result = await run_agent_for_shipment(
            shipment_id=shipment_id,
            pickup_h3=pickup_h3,
            dropoff_h3=dropoff_h3,
            cargo_type=cargo_type,
        )
        
        return {
            "status": "success",
            "shipment_id": shipment_id,
            "selected_truck": result.get("selected_truck_id"),
            "thoughts_count": len(result.get("thoughts", [])),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/agent/preferences")
async def store_user_preference(
    user_id: str,
    preference_key: str,
    preference_value: str,
) -> dict:
    """Store a user preference for future interactions."""
    entry = await vector_memory.store_user_preference(
        user_id=user_id,
        preference_key=preference_key,
        preference_value=preference_value,
    )

    return {
        "stored": True,
        "memory_id": entry.id,
        "key": preference_key,
        "value": preference_value,
    }


@router.get("/agent/preferences/{user_id}")
async def get_user_preferences(user_id: str) -> dict:
    """Get stored preferences for a user."""
    preferences = await vector_memory.get_user_preferences(user_id)

    return {
        "user_id": user_id,
        "preferences": [
            {
                "key": p.metadata.get("key", ""),
                "value": p.metadata.get("value", ""),
                "stored_at": p.created_at,
            }
            for p in preferences
        ],
    }
