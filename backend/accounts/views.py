from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = MeSerializer(request.user).data
        return Response(data)