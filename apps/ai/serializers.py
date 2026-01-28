from rest_framework import serializers


class StallMarkDataSerializer(serializers.Serializer):
    id = serializers.CharField(required=True)
    is_occupied = serializers.BooleanField(required=False)


class StallMarkSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    data = StallMarkDataSerializer(required=False, many=True)


class StallMarkModerateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    data = serializers.BooleanField(required=False)

