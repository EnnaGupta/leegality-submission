from rest_framework import serializers

from .models import Edge, Node, RouteHistory


class NodeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Node
        fields = ("id", "name")
        read_only_fields = ("id",)

    def validate_name(self, value):
        name = str(value).strip()
        if not name:
            raise serializers.ValidationError("Name is required.")
        norm = name.replace(" ", "").lower()
        if Node.objects.filter(normalized_name=norm).exists():
            raise serializers.ValidationError("Node already exists.")
        return name


def resolve_node(name_str):
    if not name_str or not isinstance(name_str, str):
        return None
    target = name_str.strip().replace(" ", "").lower()
    return Node.objects.filter(normalized_name=target).first()


class EdgeCreateSerializer(serializers.Serializer):
    source = serializers.CharField()
    destination = serializers.CharField()
    latency = serializers.FloatField()

    def validate_latency(self, value):
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0.")
        return value

    def validate(self, data):
        raw_source = data["source"].strip()
        raw_dest = data["destination"].strip()

        source_node = resolve_node(raw_source)
        if not source_node:
            raise serializers.ValidationError(
                {"source": f"Node '{raw_source}' does not exist."}
            )

        dest_node = resolve_node(raw_dest)
        if not dest_node:
            raise serializers.ValidationError(
                {"destination": f"Node '{raw_dest}' does not exist."}
            )

        if source_node == dest_node:
            raise serializers.ValidationError("Source and destination must differ.")

        if Edge.objects.filter(source=source_node, destination=dest_node).exists():
            raise serializers.ValidationError(
                f"Edge from '{source_node.name}' to '{dest_node.name}' already exists."
            )

        data["source_node"] = source_node
        data["destination_node"] = dest_node
        return data


class EdgeResponseSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.name")
    destination = serializers.CharField(source="destination.name")

    class Meta:
        model = Edge
        fields = ("id", "source", "destination", "latency")


class EdgeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = ("latency",)

    def validate_latency(self, value):
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0.")
        return value



class ShortestRouteRequestSerializer(serializers.Serializer):
    source = serializers.CharField()
    destination = serializers.CharField()

    def validate(self, data):
        raw_source = data["source"].strip()
        raw_dest = data["destination"].strip()

        source_node = resolve_node(raw_source)
        if not source_node:
            raise serializers.ValidationError(
                {"source": f"Node '{raw_source}' does not exist."}
            )

        dest_node = resolve_node(raw_dest)
        if not dest_node:
            raise serializers.ValidationError(
                {"destination": f"Node '{raw_dest}' does not exist."}
            )

        data["source_node"] = source_node
        data["destination_node"] = dest_node
        return data


class RouteHistorySerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.name")
    destination = serializers.CharField(source="destination.name")

    class Meta:
        model = RouteHistory
        fields = "__all__"
