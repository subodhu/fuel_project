from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RouteRequestSerializer
from .utils import get_route_and_optimize


class HealthCheckAPIView(APIView):
    """Health check endpoint"""

    def get(self, request):
        return Response(
            {"status": "healthy", "service": "Fuel Project API"},
            status=status.HTTP_200_OK,
        )


class RouteAPIView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data.get("start_location")
        finish = serializer.validated_data.get("finish_location")

        data, error = get_route_and_optimize(start, finish)

        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data)
