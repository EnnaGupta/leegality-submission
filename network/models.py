from django.db import models


class Node(models.Model):
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "network_nodes"

    def save(self, *args, **kwargs):
        if self.name:
            self.normalized_name = self.name.strip().replace(" ", "").lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Edge(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing_edges")
    destination = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_edges")
    latency = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "network_edges"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "destination"],
                name="unique_directed_edge",
            ),
        ]

    def __str__(self):
        return f"{self.source.name} → {self.destination.name} ({self.latency})"


class RouteHistory(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="route_sources")
    destination = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="route_destinations")
    total_latency = models.FloatField()
    path = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "network_route_history"

    def __str__(self):
        return f"{self.source.name} → {self.destination.name} ({self.total_latency})"
