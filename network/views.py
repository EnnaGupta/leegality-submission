from django.shortcuts import render
from django.views import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Edge, Node, RouteHistory
from .serializers import (
    EdgeCreateSerializer,
    EdgeResponseSerializer,
    EdgeUpdateSerializer,
    NodeSerializer,
    RouteHistorySerializer,
    ShortestRouteRequestSerializer,
)
from .services.cache_service import get_adjacency_list, invalidate_cache
from .services.graph_service import find_shortest_path


class HomeView(View):
   
    def get(self, request):
        return render(request, "index.html")


class NodeView(APIView):

    serializer_class = NodeSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request):
        nodes = Node.objects.all().order_by("-id")
        serializer = self.get_serializer(nodes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        raw_name = request.data.get("name")
        if not raw_name or not str(raw_name).strip():
            return Response(
                {"name": ["Name is required"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        display_name = str(raw_name).strip()
        norm = display_name.replace(" ", "").lower()
        if Node.objects.filter(normalized_name=norm).exists():
            return Response(
                {"name": ["Node already exists"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data={"name": display_name})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NodeDetailView(APIView):

    def delete(self, request, id):
        try:
            node = Node.objects.get(id=id)
        except Node.DoesNotExist:
            return Response(
                {"error": "Node not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        node.delete()
        invalidate_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EdgeView(APIView):

    serializer_class = EdgeResponseSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request):
        edges = Edge.objects.select_related("source", "destination").all().order_by("-id")
        serializer = self.get_serializer(edges, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EdgeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        s_node = serializer.validated_data["source_node"]
        d_node = serializer.validated_data["destination_node"]
        lat = serializer.validated_data["latency"]

        edge = Edge.objects.create(
            source=s_node,
            destination=d_node,
            latency=lat,
        )
        invalidate_cache()

        response_data = self.get_serializer(edge).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class EdgeDetailView(APIView):
    serializer_class = EdgeUpdateSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def put(self, request, id):
        try:
            edge = Edge.objects.select_related("source", "destination").get(id=id)
        except Edge.DoesNotExist:
            return Response(
                {"error": "Edge not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(edge, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_cache()
        return Response(EdgeResponseSerializer(edge).data, status=status.HTTP_200_OK)

    def delete(self, request, id):

        try:
            edge = Edge.objects.get(id=id)
        except Edge.DoesNotExist:
            return Response(
                {"error": "Edge not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        edge.delete()
        invalidate_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShortestRouteView(APIView):

    serializer_class = ShortestRouteRequestSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source_node = serializer.validated_data["source_node"]
        dest_node = serializer.validated_data["destination_node"]

        # Fetch graph and find shortest route
        graph = get_adjacency_list()
        # using Dijkstra's algorithm
        result = find_shortest_path(graph, source_node.name, dest_node.name)

        if result is None:
            return Response(
                {
                    "error": (
                        f"No path exists between "
                        f"{source_node.name} and {dest_node.name}"
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        total_latency, path = result

        RouteHistory.objects.create(
            source=source_node,
            destination=dest_node,
            total_latency=total_latency,
            path=path,
        )

        return Response(
            {"total_latency": total_latency, "path": path},
            status=status.HTTP_200_OK,
        )


class RouteHistoryView(APIView):

    serializer_class = RouteHistorySerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get(self, request):
        qs = RouteHistory.objects.select_related("source", "destination").all().order_by("-created_at")

        source = request.query_params.get("source")
        destination = request.query_params.get("destination")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        limit = request.query_params.get("limit")

        if source:
            qs = qs.filter(source__normalized_name=source.strip().replace(" ", "").lower())
        if destination:
            qs = qs.filter(destination__normalized_name=destination.strip().replace(" ", "").lower())
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        if limit:
            try:
                qs = qs[: int(limit)]
            except (ValueError, TypeError):
                pass 
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
