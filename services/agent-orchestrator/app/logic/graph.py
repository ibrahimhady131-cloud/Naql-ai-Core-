"""LangGraph-based autonomous planning for shipment matching."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, StateGraph


class AgentState(TypedDict, total=False):
    """State passed through the agent graph."""

    shipment_id: str
    pickup_h3: str
    dropoff_h3: str
    cargo_type: str

    # Analysis results
    nearby_trucks: list
    truck_details: list
    ranked_trucks: list
    selected_truck_id: str | None

    # Reasoning log
    thoughts: list


async def planner_node(state: AgentState) -> AgentState:
    """Analyze the shipment and determine requirements."""
    shipment_id = state["shipment_id"]
    cargo_type = state["cargo_type"]

    thought = f"[Agent] Planner: Analyzing shipment {shipment_id}"
    thought += f" - Cargo type: {cargo_type}"
    state["thoughts"].append(thought)
    print(thought)

    return state


async def fleet_analyzer_node(state: AgentState) -> AgentState:
    """Fetch available trucks via gRPC calls."""
    shipment_id = state["shipment_id"]
    pickup_h3 = state["pickup_h3"]

    thought = f"[Agent] Fleet-Analyzer: Searching for trucks near H3 {pickup_h3}"
    state["thoughts"].append(thought)
    print(thought)

    try:
        from ..tools.service_tools import service_client
        from ..core.config import settings

        # Get trucks from Fleet Service via HTTP
        result = await service_client._call("GET", f"{settings.FLEET_SERVICE_URL}/api/v1/trucks")
        if result.success and result.data:
            trucks = result.data.get("trucks", [])
            # Filter to get available trucks (simplified - in production would filter by location)
            available = [t for t in trucks if t.get("status") == "available"]
            state["nearby_trucks"] = available[:10]  # Limit to 10

            thought = f"[Agent] Fleet-Analyzer: Found {len(state['nearby_trucks'])} available trucks"
            state["thoughts"].append(thought)
            print(thought)

            # Get detailed info for each truck via gRPC
            for truck in state["nearby_trucks"]:
                truck_id = truck.get("id")
                if truck_id:
                    try:
                        import sys
                        import os
                        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "matching-engine"))
                        from app.grpc_client import get_fleet_client

                        fleet_client = get_fleet_client()
                        details = await fleet_client.get_truck_details(truck_id)
                        if details:
                            state["truck_details"].append({
                                "truck_id": str(truck_id),
                                "truck_type": details.truck_type,
                                "load_capacity_kg": details.load_capacity_kg,
                                "fuel_level_pct": details.fuel_level_pct,
                                "status": details.status,
                            })
                    except Exception as e:
                        print(f"[Agent] Warning: Could not get details for truck {truck_id}: {e}")

    except Exception as e:
        thought = f"[Agent] Fleet-Analyzer: Error fetching trucks: {e}"
        state["thoughts"].append(thought)
        print(thought)

    return state


async def decision_maker_node(state: AgentState) -> AgentState:
    """Rank trucks and select the best match based on logic."""
    thought = f"[Agent] Decision-Maker: Analyzing {len(state['truck_details'])} trucks for best match"
    state["thoughts"].append(thought)
    print(thought)

    if not state["truck_details"]:
        thought = "[Agent] Decision-Maker: No trucks available for matching"
        state["thoughts"].append(thought)
        print(thought)
        return state

    # Logic-based ranking (simulating LLM reasoning)
    # Score trucks based on: capacity match, fuel level, availability
    ranked = []
    for truck in state["truck_details"]:
        score = 0

        # Capacity scoring (simplified - assume general cargo ~5000kg)
        capacity = truck.get("load_capacity_kg", 0)
        if capacity >= 5000:
            score += 50
        elif capacity >= 2000:
            score += 30

        # Fuel scoring
        fuel = truck.get("fuel_level_pct", 0)
        score += fuel * 0.3  # 30% weight on fuel

        # Status bonus
        if truck.get("status") == "available":
            score += 20

        ranked.append({**truck, "match_score": score})

    # Sort by score descending
    ranked.sort(key=lambda x: x["match_score"], reverse=True)
    state["ranked_trucks"] = ranked

    # Select best
    if ranked:
        best = ranked[0]
        state["selected_truck_id"] = best["truck_id"]

        thought = f"[Agent] Decision-Maker: Selected truck {best['truck_id']} (score: {best['match_score']:.1f})"
        state["thoughts"].append(thought)
        print(thought)

        # Log top 3 options
        for i, truck in enumerate(ranked[:3]):
            thought = f"[Agent] Option {i+1}: Truck {truck['truck_id']} - Score: {truck['match_score']:.1f}, Capacity: {truck.get('load_capacity_kg', 0)}kg, Fuel: {truck.get('fuel_level_pct', 0)}%"
            state["thoughts"].append(thought)
            print(thought)

    return state


def create_agent_graph() -> StateGraph:
    """Create the LangGraph state machine for autonomous planning."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("fleet_analyzer", fleet_analyzer_node)
    workflow.add_node("decision_maker", decision_maker_node)

    # Define flow
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "fleet_analyzer")
    workflow.add_edge("fleet_analyzer", "decision_maker")
    workflow.add_edge("decision_maker", END)

    return workflow.compile()


async def run_agent_for_shipment(
    shipment_id: str,
    pickup_h3: str,
    dropoff_h3: str,
    cargo_type: str,
) -> AgentState:
    """Execute the agent graph for a shipment."""
    initial_state: AgentState = {
        "shipment_id": shipment_id,
        "pickup_h3": pickup_h3,
        "dropoff_h3": dropoff_h3,
        "cargo_type": cargo_type,
        "nearby_trucks": [],
        "truck_details": [],
        "ranked_trucks": [],
        "selected_truck_id": None,
        "thoughts": [],
    }

    graph = create_agent_graph()
    final_state = await graph.ainvoke(initial_state)

    return final_state
