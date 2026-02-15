from django.urls import path
from api.views import RouteAPIView, HealthCheckAPIView


urlpatterns = [
    path("route/", RouteAPIView.as_view(), name="route"),
    path("health/", HealthCheckAPIView.as_view(), name="health"),
]
