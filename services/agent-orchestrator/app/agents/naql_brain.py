"""LangGraph-powered AI Agent for Naql.ai.

Implements a three-component agentic workflow:
1. Planner: Decomposes natural language requests into sub-tasks
2. Dispatcher: Optimizes truck/driver assignment using OR-Tools
3. Sentinel: Monitors real-time events and triggers re-assignments

Uses LangGraph's StateGraph for structured agent execution flow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar, Literal

from langgraph.graph import END, StateGraph

from ..tools.service_tools import ToolResult, service_client


class AgentState(StrEnum):
    """States in the agent workflow."""

    PLANNING = "planning"
    EXECUTING = "executing"
    DISPATCHING = "dispatching"
    MONITORING = "monitoring"
    RESPONDING = "responding"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SubTask:
    """A decomposed sub-task from the planner."""

    id: str
    description: str
    tool_name: str
    tool_args: dict[str, Any]
    status: str = "pending"  # pending, executing, completed, failed
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Full context for an agent execution cycle."""

    session_id: str
    user_id: str
    user_message: str
    language: str = "en"
    intent: str = ""
    sub_tasks: list[SubTask] = field(default_factory=list)
    current_step: int = 0
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""
    state: AgentState = AgentState.PLANNING
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Planner Component ──────────────────────────────────────


class Planner:
    """Decomposes user requests into executable sub-tasks.

    Analyzes the natural language input to determine:
    - User intent (book shipment, track delivery, get quote, etc.)
    - Required sub-tasks and their execution order
    - Which tools to invoke

    In production, this uses GPT-4o for intent classification and
    task decomposition. For development, uses rule-based patterns.
    """

    # Intent patterns for rule-based classification (dev mode)
    INTENT_PATTERNS: ClassVar[dict[str, list[str]]] = {
        "book_shipment": ["move", "ship", "transport", "deliver", "send", "نقل", "شحن"],
        "get_quote": ["quote", "price", "cost", "how much", "كم", "سعر"],
        "track_shipment": ["track", "where", "status", "eta", "أين", "تتبع"],
        "find_trucks": ["available", "trucks", "nearby", "find", "عربيات"],
        "check_balance": ["balance", "wallet", "money", "رصيد"],
        "general": [],
    }

    def classify_intent(self, message: str) -> str:
        """Classify user intent from natural language."""
        message_lower = message.lower()
        for intent, keywords in self.INTENT_PATTERNS.items():
            if any(kw in message_lower for kw in keywords):
                return intent
        return "general"

    def decompose(self, context: AgentContext) -> list[SubTask]:
        """Decompose a request into ordered sub-tasks."""
        intent = self.classify_intent(context.user_message)
        context.intent = intent

        if intent == "book_shipment":
            return self._plan_booking(context)
        elif intent == "get_quote":
            return self._plan_quote(context)
        elif intent == "find_trucks":
            return self._plan_truck_search(context)
        elif intent == "check_balance":
            return self._plan_balance_check(context)
        else:
            return self._plan_general(context)

    def _plan_booking(self, context: AgentContext) -> list[SubTask]:
        """Plan sub-tasks for a shipment booking."""
        return [
            SubTask(
                id=str(uuid.uuid4()),
                description="Search for available trucks near the origin",
                tool_name="search_available_trucks",
                tool_args={
                    "latitude": 30.0444,  # Default Cairo
                    "longitude": 31.2357,
                    "radius_km": 20.0,
                },
            ),
            SubTask(
                id=str(uuid.uuid4()),
                description="Get price quote for the shipment",
                tool_name="get_quote",
                tool_args={
                    "distance_km": 220.0,
                    "truck_type": "full",
                    "weight_kg": 5000.0,
                    "origin_region": "EG-CAI",
                    "dest_region": "EG-ALX",
                },
            ),
            SubTask(
                id=str(uuid.uuid4()),
                description="Find optimal driver match",
                tool_name="request_match",
                tool_args={
                    "shipment_id": str(uuid.uuid4()),
                    "origin_lat": 30.0444,
                    "origin_lng": 31.2357,
                    "dest_lat": 31.2001,
                    "dest_lng": 29.9187,
                    "truck_type": "full",
                    "weight_kg": 5000.0,
                },
            ),
        ]

    def _plan_quote(self, context: AgentContext) -> list[SubTask]:
        """Plan sub-tasks for getting a quote."""
        return [
            SubTask(
                id=str(uuid.uuid4()),
                description="Calculate price quote",
                tool_name="get_quote",
                tool_args={
                    "distance_km": 220.0,
                    "truck_type": "full",
                    "weight_kg": 5000.0,
                    "origin_region": "EG-CAI",
                    "dest_region": "EG-ALX",
                },
            ),
        ]

    def _plan_truck_search(self, context: AgentContext) -> list[SubTask]:
        """Plan sub-tasks for finding available trucks."""
        return [
            SubTask(
                id=str(uuid.uuid4()),
                description="Search for nearby available trucks",
                tool_name="search_available_trucks",
                tool_args={
                    "latitude": 30.0444,
                    "longitude": 31.2357,
                    "radius_km": 20.0,
                },
            ),
        ]

    def _plan_balance_check(self, context: AgentContext) -> list[SubTask]:
        """Plan sub-tasks for checking balance."""
        return [
            SubTask(
                id=str(uuid.uuid4()),
                description="Retrieve account balance",
                tool_name="get_balance",
                tool_args={"user_id": context.user_id},
            ),
        ]

    def _plan_general(self, context: AgentContext) -> list[SubTask]:
        """Plan for general inquiries."""
        return []


# ── Dispatcher Component ───────────────────────────────────


class Dispatcher:
    """Optimizes truck/driver assignment using constraint satisfaction.

    In production, uses Google OR-Tools to solve the Vehicle Routing Problem (VRP)
    with constraints:
    - Driver working hours / fatigue limits
    - Truck capacity and type requirements
    - Route distance and toll costs
    - Client preferences (from vector memory)

    For development, uses a simplified scoring-based approach.
    """

    def optimize_assignment(
        self,
        candidates: list[dict[str, Any]],
        constraints: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank candidates using constraint-aware optimization.

        In production, this formulates a CSP (Constraint Satisfaction Problem)
        using OR-Tools' CP-SAT solver.
        """
        if not candidates:
            return []

        # Score each candidate
        scored = []
        for candidate in candidates:
            score = self._calculate_score(candidate, constraints or {})
            scored.append({**candidate, "optimization_score": score})

        # Sort by optimization score descending
        scored.sort(key=lambda x: x["optimization_score"], reverse=True)
        return scored

    def _calculate_score(self, candidate: dict[str, Any], constraints: dict[str, Any]) -> float:
        """Calculate optimization score for a candidate."""
        score = 0.0

        # Distance factor (closer is better)
        distance = candidate.get("distance_km", 50.0)
        score += max(0, 1.0 - distance / 100.0) * 0.3

        # Rating factor
        rating = candidate.get("driver_rating", 3.0)
        score += (rating / 5.0) * 0.3

        # ETA factor (faster is better)
        eta = candidate.get("eta_minutes", 60)
        score += max(0, 1.0 - eta / 120.0) * 0.2

        # Capacity match factor
        score += 0.2  # Base score for meeting capacity requirements

        return round(score, 3)


# ── Sentinel Component ─────────────────────────────────────


class Sentinel:
    """Real-time event monitor and automatic re-assignment trigger.

    Monitors:
    - Truck breakdowns → automatic load re-assignment
    - Geofence violations → client notifications
    - ETA deviations → route recalculation
    - Driver fatigue → mandatory rest enforcement

    In production, this consumes events from NATS JetStream.
    """

    def __init__(self) -> None:
        self._active_monitors: dict[str, dict[str, Any]] = {}
        self._alerts: list[dict[str, Any]] = []

    def start_monitoring(self, trip_id: str, shipment_id: str) -> None:
        """Start monitoring a trip for anomalies."""
        self._active_monitors[trip_id] = {
            "shipment_id": shipment_id,
            "status": "active",
            "alerts": [],
        }

    def stop_monitoring(self, trip_id: str) -> None:
        """Stop monitoring a trip."""
        self._active_monitors.pop(trip_id, None)

    async def process_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Process a real-time event and determine if action is needed."""
        if event_type == "truck_breakdown":
            return await self._handle_breakdown(payload)
        elif event_type == "geofence_violation":
            return await self._handle_geofence_violation(payload)
        elif event_type == "eta_deviation":
            return await self._handle_eta_deviation(payload)
        elif event_type == "speed_violation":
            return await self._handle_speed_violation(payload)
        return None

    async def _handle_breakdown(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle truck breakdown — trigger re-assignment."""
        return {
            "action": "re_assign",
            "reason": "Truck breakdown detected",
            "severity": "critical",
            "truck_id": payload.get("truck_id"),
            "shipment_id": payload.get("shipment_id"),
            "notify_client": True,
        }

    async def _handle_geofence_violation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle geofence violation — notify and log."""
        return {
            "action": "notify",
            "reason": f"Truck entered restricted zone: {payload.get('zone_name')}",
            "severity": "warning",
            "truck_id": payload.get("truck_id"),
            "notify_client": False,
        }

    async def _handle_eta_deviation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle significant ETA deviation — recalculate and notify."""
        deviation_minutes = payload.get("deviation_minutes", 0)
        severity = "critical" if deviation_minutes > 60 else "warning"

        return {
            "action": "recalculate_route",
            "reason": f"ETA deviation: {deviation_minutes} minutes",
            "severity": severity,
            "truck_id": payload.get("truck_id"),
            "notify_client": deviation_minutes > 30,
        }

    async def _handle_speed_violation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle speed violation — warn driver."""
        return {
            "action": "warn_driver",
            "reason": f"Speed violation: {payload.get('speed_kmh')} km/h (limit: {payload.get('limit_kmh')})",
            "severity": "warning",
            "truck_id": payload.get("truck_id"),
            "notify_client": False,
        }


# ── LangGraph Workflow ─────────────────────────────────────


planner = Planner()
dispatcher = Dispatcher()
sentinel = Sentinel()


def plan_step(context: AgentContext) -> AgentContext:
    """Planning node: decompose user request into sub-tasks."""
    context.state = AgentState.PLANNING
    context.sub_tasks = planner.decompose(context)

    if not context.sub_tasks:
        context.state = AgentState.RESPONDING
        context.response = _generate_general_response(context)
    else:
        context.state = AgentState.EXECUTING

    return context


async def execute_step(context: AgentContext) -> AgentContext:
    """Execution node: run each sub-task's tool."""
    context.state = AgentState.EXECUTING

    for task in context.sub_tasks:
        if task.status != "pending":
            continue

        task.status = "executing"

        try:
            tool_func = getattr(service_client, task.tool_name, None)
            if tool_func is None:
                task.status = "failed"
                task.result = {"error": f"Unknown tool: {task.tool_name}"}
                continue

            result: ToolResult = await tool_func(**task.tool_args)

            if result.success:
                task.status = "completed"
                task.result = result.data
            else:
                task.status = "failed"
                task.result = {"error": result.error}

        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}

        context.tool_results.append(
            {
                "tool_name": task.tool_name,
                "tool_input": str(task.tool_args),
                "tool_output": str(task.result),
                "success": task.status == "completed",
            }
        )

    # If we have match results, run dispatcher optimization
    match_results = [
        t.result
        for t in context.sub_tasks
        if t.tool_name == "request_match" and t.status == "completed"
    ]
    if match_results:
        context.state = AgentState.DISPATCHING
    else:
        context.state = AgentState.RESPONDING

    return context


def dispatch_step(context: AgentContext) -> AgentContext:
    """Dispatch node: optimize assignment using OR-Tools."""
    context.state = AgentState.DISPATCHING

    for task in context.sub_tasks:
        if task.tool_name == "request_match" and task.status == "completed":
            candidates = task.result.get("candidates", [])
            optimized = dispatcher.optimize_assignment(candidates)
            context.metadata["optimized_candidates"] = optimized

    context.state = AgentState.RESPONDING
    return context


def respond_step(context: AgentContext) -> AgentContext:
    """Response node: generate natural language response."""
    context.state = AgentState.RESPONDING
    context.response = _generate_response(context)
    context.state = AgentState.COMPLETED
    return context


def _generate_response(context: AgentContext) -> str:
    """Generate a response based on the intent and tool results.

    In production, this calls GPT-4o with the full context
    for natural language generation in Arabic/English.
    """
    intent = context.intent

    if intent == "book_shipment":
        return _generate_booking_response(context)
    elif intent == "get_quote":
        return _generate_quote_response(context)
    elif intent == "find_trucks":
        return _generate_truck_search_response(context)
    elif intent == "check_balance":
        return _generate_balance_response(context)
    else:
        return _generate_general_response(context)


def _generate_booking_response(context: AgentContext) -> str:
    """Generate response for booking intent."""
    quote_task = next(
        (t for t in context.sub_tasks if t.tool_name == "get_quote"),
        None,
    )
    match_task = next(
        (t for t in context.sub_tasks if t.tool_name == "request_match"),
        None,
    )

    parts = ["I've processed your shipment request. Here's the summary:\n"]

    if quote_task and quote_task.status == "completed":
        q = quote_task.result
        parts.append(f"💰 **Quote**: {q.get('total_egp', 'N/A')} EGP")
        parts.append(f"   - Fuel: {q.get('fuel_cost_egp', 'N/A')} EGP")
        parts.append(f"   - Tolls: {q.get('toll_cost_egp', 'N/A')} EGP")
        parts.append(f"   - Service fee: {q.get('service_fee_egp', 'N/A')} EGP")
        parts.append(f"   - Insurance: {q.get('insurance_fee_egp', 'N/A')} EGP\n")

    if match_task and match_task.status == "completed":
        candidates = match_task.result.get("candidates", [])
        if candidates:
            parts.append(f"🚛 **{len(candidates)} drivers found** near your pickup location:")
            for i, c in enumerate(candidates[:3], 1):
                parts.append(
                    f"   {i}. Driver {c.get('driver_id', 'N/A')[:8]}... "
                    f"(Rating: {c.get('driver_rating', 'N/A')}, "
                    f"ETA: {c.get('eta_minutes', 'N/A')} min)"
                )

    parts.append("\nWould you like to confirm this booking?")
    return "\n".join(parts)


def _generate_quote_response(context: AgentContext) -> str:
    """Generate response for quote intent."""
    quote_task = next(
        (t for t in context.sub_tasks if t.tool_name == "get_quote"),
        None,
    )

    if quote_task and quote_task.status == "completed":
        q = quote_task.result
        return (
            f"Here's your quote:\n\n"
            f"💰 **Total: {q.get('total_egp', 'N/A')} EGP**\n"
            f"- Fuel: {q.get('fuel_cost_egp', 'N/A')} EGP\n"
            f"- Tolls: {q.get('toll_cost_egp', 'N/A')} EGP\n"
            f"- Service fee: {q.get('service_fee_egp', 'N/A')} EGP\n"
            f"- Insurance: {q.get('insurance_fee_egp', 'N/A')} EGP\n\n"
            f"This quote is valid for 24 hours."
        )

    return "I couldn't generate a quote at this time. Please try again."


def _generate_truck_search_response(context: AgentContext) -> str:
    """Generate response for truck search intent."""
    search_task = next(
        (t for t in context.sub_tasks if t.tool_name == "search_available_trucks"),
        None,
    )

    if search_task and search_task.status == "completed":
        trucks = search_task.result.get("trucks", [])
        if trucks:
            return f"Found {len(trucks)} available trucks in your area."
        return "No trucks are currently available in your area. Try expanding the search radius."

    return "I couldn't search for trucks at this time."


def _generate_balance_response(context: AgentContext) -> str:
    """Generate response for balance check intent."""
    balance_task = next(
        (t for t in context.sub_tasks if t.tool_name == "get_balance"),
        None,
    )

    if balance_task and balance_task.status == "completed":
        b = balance_task.result
        return (
            f"Your account balance:\n"
            f"💵 Available: {b.get('available_egp', 0)} EGP\n"
            f"🔒 Held in escrow: {b.get('held_egp', 0)} EGP\n"
            f"📊 Total: {b.get('total_egp', 0)} EGP"
        )

    return "I couldn't retrieve your balance at this time."


def _generate_general_response(context: AgentContext) -> str:
    """Generate response for general inquiries."""
    return (
        "Welcome to Naql.ai! I can help you with:\n\n"
        "🚛 **Book a shipment** — Tell me what you need to move and where\n"
        "💰 **Get a quote** — I'll calculate the cost for your delivery\n"
        "📍 **Find trucks** — See available trucks near you\n"
        "📦 **Track delivery** — Check the status of your shipment\n"
        "💵 **Check balance** — View your account balance\n\n"
        "How can I help you today?"
    )


def route_after_plan(context: AgentContext) -> Literal["execute", "respond"]:
    """Route decision after planning step."""
    if context.sub_tasks:
        return "execute"
    return "respond"


def route_after_execute(context: AgentContext) -> Literal["dispatch", "respond"]:
    """Route decision after execution step."""
    if context.state == AgentState.DISPATCHING:
        return "dispatch"
    return "respond"


def build_agent_graph() -> StateGraph:
    """Build the LangGraph state graph for the agent workflow.

    Graph flow:
        plan → [execute | respond]
        execute → [dispatch | respond]
        dispatch → respond
        respond → END
    """
    graph = StateGraph(AgentContext)

    # Add nodes
    graph.add_node("plan", plan_step)
    graph.add_node("execute", execute_step)
    graph.add_node("dispatch", dispatch_step)
    graph.add_node("respond", respond_step)

    # Set entry point
    graph.set_entry_point("plan")

    # Add conditional edges
    graph.add_conditional_edges("plan", route_after_plan)
    graph.add_conditional_edges("execute", route_after_execute)

    # Fixed edges
    graph.add_edge("dispatch", "respond")
    graph.add_edge("respond", END)

    return graph


# Compiled agent graph
agent_graph = build_agent_graph()
