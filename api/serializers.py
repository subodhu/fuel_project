from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField()
    finish_location = serializers.CharField()

    def validate(self, data):
        start = data["start_location"]
        end = data["finish_location"]
        if start == end:
            raise serializers.ValidationError(
                "Start and finish locations must be different"
            )
        return data
