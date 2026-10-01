from django.urls import path

from .views import (
    EdgeDetailView,
    EdgeView,
    HomeView,
    NodeDetailView,
    NodeView,
    RouteHistoryView,
    ShortestRouteView,
)

urlpatterns = [
    # --- Frontend Dashboard ---
    path("", HomeView.as_view(), name="home"),

    # --- Nodes ---
    path("nodes", NodeView.as_view(), name="nodes"),
    path("nodes/<int:id>", NodeDetailView.as_view(), name="node-detail"),

    path("edges", EdgeView.as_view(), name="edges"),
    path("edges/<int:id>", EdgeDetailView.as_view(), name="edge-detail"),

    path("routes/shortest", ShortestRouteView.as_view(), name="shortest-route"),
    path("routes/history", RouteHistoryView.as_view(), name="route-history"),
]
