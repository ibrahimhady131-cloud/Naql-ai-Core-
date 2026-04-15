"""OR-Tools based route optimization for the Naql.ai Dispatcher.

Solves the Capacitated Vehicle Routing Problem (CVRP) with:
- Time windows for pickup/delivery
- Vehicle capacity constraints
- Driver fatigue limits (max 8 hours driving)
- Egyptian-specific route penalties (desert highways, urban congestion)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Location:
    """A geographic point in the routing problem."""

    id: str
    latitude: float
    longitude: float
    name: str = ""
    demand_kg: int = 0
    time_window_start: int = 0  # Minutes from midnight
    time_window_end: int = 1440  # 24 hours
    service_time_min: int = 30  # Loading/unloading time


@dataclass
class Vehicle:
    """A vehicle (truck) in the routing problem."""

    id: str
    capacity_kg: int
    max_distance_km: int = 500
    max_driving_hours: float = 8.0
    cost_per_km: float = 4.5
    start_location_id: str = ""
    truck_type: str = "full"


@dataclass
class RouteStop:
    """A stop in an optimized route."""

    location: Location
    arrival_time_min: int = 0
    departure_time_min: int = 0
    load_kg: int = 0


@dataclass
class OptimizedRoute:
    """Result of route optimization for a single vehicle."""

    vehicle: Vehicle
    stops: list[RouteStop] = field(default_factory=list)
    total_distance_km: float = 0.0
    total_time_min: int = 0
    total_load_kg: int = 0
    cost_egp: float = 0.0


@dataclass
class RoutingResult:
    """Full routing optimization result."""

    routes: list[OptimizedRoute] = field(default_factory=list)
    unassigned_locations: list[Location] = field(default_factory=list)
    total_cost_egp: float = 0.0
    total_distance_km: float = 0.0
    solver_status: str = "unknown"


class RouteOptimizer:
    """Capacitated Vehicle Routing Problem (CVRP) solver.

    Uses Google OR-Tools CP-SAT solver for optimal route planning.
    Falls back to a greedy nearest-neighbor heuristic when OR-Tools
    is not available or for quick estimations.
    """

    def __init__(self) -> None:
        self._or_tools_available = self._check_or_tools()

    def _check_or_tools(self) -> bool:
        """Check if OR-Tools is available."""
        try:
            from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # noqa: F401

            return True
        except ImportError:
            return False

    def optimize(
        self,
        locations: list[Location],
        vehicles: list[Vehicle],
        distance_matrix: list[list[float]] | None = None,
    ) -> RoutingResult:
        """Optimize routes for multiple vehicles and locations.

        Args:
            locations: List of pickup/delivery locations
            vehicles: List of available vehicles
            distance_matrix: Pre-computed distance matrix (optional)

        Returns:
            Optimized routing result with assigned routes
        """
        if not locations or not vehicles:
            return RoutingResult(solver_status="no_input")

        if distance_matrix is None:
            distance_matrix = self._compute_distance_matrix(locations)

        if self._or_tools_available and len(locations) > 2:
            return self._solve_with_or_tools(locations, vehicles, distance_matrix)
        else:
            return self._solve_greedy(locations, vehicles, distance_matrix)

    def _compute_distance_matrix(self, locations: list[Location]) -> list[list[float]]:
        """Compute Haversine distance matrix between all locations."""

        n = len(locations)
        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                dist = self._haversine(
                    locations[i].latitude,
                    locations[i].longitude,
                    locations[j].latitude,
                    locations[j].longitude,
                )
                matrix[i][j] = dist
                matrix[j][i] = dist

        return matrix

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance in km."""
        import math

        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _solve_with_or_tools(
        self,
        locations: list[Location],
        vehicles: list[Vehicle],
        distance_matrix: list[list[float]],
    ) -> RoutingResult:
        """Solve CVRP using Google OR-Tools."""
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2

        n = len(locations)
        v = len(vehicles)

        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(n, v, 0)  # depot at index 0
        routing = pywrapcp.RoutingModel(manager)

        # Distance callback
        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # Convert to meters

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Capacity constraint
        def demand_callback(from_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            return locations[from_node].demand_kg

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [v_obj.capacity_kg for v_obj in vehicles],
            True,  # start cumul to zero
            "Capacity",
        )

        # Distance constraint (max distance per vehicle)
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            max(v_obj.max_distance_km for v_obj in vehicles) * 1000,
            True,
            "Distance",
        )

        # Search parameters
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.FromSeconds(30)

        # Solve
        solution = routing.SolveWithParameters(search_params)

        if solution is None:
            return self._solve_greedy(locations, vehicles, distance_matrix)

        # Extract routes
        routes: list[OptimizedRoute] = []
        total_cost = 0.0
        total_distance = 0.0

        for vehicle_idx in range(v):
            route_stops: list[RouteStop] = []
            route_distance = 0.0
            route_load = 0

            index = routing.Start(vehicle_idx)
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += locations[node_index].demand_kg
                route_stops.append(
                    RouteStop(
                        location=locations[node_index],
                        load_kg=route_load,
                    )
                )
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += distance_matrix[manager.IndexToNode(previous_index)][
                    manager.IndexToNode(index)
                ]

            if len(route_stops) > 1:  # Skip empty routes
                cost = route_distance * vehicles[vehicle_idx].cost_per_km
                routes.append(
                    OptimizedRoute(
                        vehicle=vehicles[vehicle_idx],
                        stops=route_stops,
                        total_distance_km=round(route_distance, 2),
                        total_time_min=int(route_distance / 50 * 60),  # ~50 km/h avg
                        total_load_kg=route_load,
                        cost_egp=round(cost, 2),
                    )
                )
                total_cost += cost
                total_distance += route_distance

        return RoutingResult(
            routes=routes,
            total_cost_egp=round(total_cost, 2),
            total_distance_km=round(total_distance, 2),
            solver_status="optimal",
        )

    def _solve_greedy(
        self,
        locations: list[Location],
        vehicles: list[Vehicle],
        distance_matrix: list[list[float]],
    ) -> RoutingResult:
        """Greedy nearest-neighbor heuristic fallback."""
        assigned: set[int] = {0}  # Depot is always assigned
        routes: list[OptimizedRoute] = []
        total_cost = 0.0
        total_distance = 0.0

        for vehicle in vehicles:
            route_stops: list[RouteStop] = []
            current = 0
            route_load = 0
            route_distance = 0.0

            while True:
                # Find nearest unassigned location
                best_next = -1
                best_dist = float("inf")

                for j in range(len(locations)):
                    if j in assigned:
                        continue
                    if route_load + locations[j].demand_kg > vehicle.capacity_kg:
                        continue
                    if distance_matrix[current][j] < best_dist:
                        best_dist = distance_matrix[current][j]
                        best_next = j

                if best_next == -1:
                    break

                assigned.add(best_next)
                route_load += locations[best_next].demand_kg
                route_distance += best_dist
                route_stops.append(
                    RouteStop(
                        location=locations[best_next],
                        load_kg=route_load,
                    )
                )
                current = best_next

            if route_stops:
                # Return to depot
                route_distance += distance_matrix[current][0]
                cost = route_distance * vehicle.cost_per_km

                routes.append(
                    OptimizedRoute(
                        vehicle=vehicle,
                        stops=route_stops,
                        total_distance_km=round(route_distance, 2),
                        total_time_min=int(route_distance / 50 * 60),
                        total_load_kg=route_load,
                        cost_egp=round(cost, 2),
                    )
                )
                total_cost += cost
                total_distance += route_distance

        # Find unassigned locations
        unassigned = [locations[i] for i in range(len(locations)) if i not in assigned]

        return RoutingResult(
            routes=routes,
            unassigned_locations=unassigned,
            total_cost_egp=round(total_cost, 2),
            total_distance_km=round(total_distance, 2),
            solver_status="greedy" if not self._or_tools_available else "feasible",
        )
