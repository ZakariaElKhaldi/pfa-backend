from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin

from .models import ManipulationFlag, RetrainLog
from .serializers import ManipulationFlagSerializer, RetrainLogSerializer


class ManipulationFlagListView(generics.ListAPIView):
    """GET /api/intelligence/flags/ — admin only, newest first."""
    serializer_class = ManipulationFlagSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = ManipulationFlag.objects.all()
        reviewed = self.request.query_params.get("reviewed")
        if reviewed == "false":
            qs = qs.filter(reviewed=False)
        elif reviewed == "true":
            qs = qs.filter(reviewed=True)
        return qs


class ManipulationFlagReviewView(APIView):
    """PATCH /api/intelligence/flags/<pk>/review/ — marks flag as reviewed."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            flag = ManipulationFlag.objects.get(pk=pk)
        except ManipulationFlag.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        flag.reviewed = True
        flag.save(update_fields=["reviewed"])
        return Response(ManipulationFlagSerializer(flag).data)


class RetrainLogListView(generics.ListAPIView):
    """GET /api/intelligence/retrain-logs/ — admin only, newest first."""
    serializer_class = RetrainLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = RetrainLog.objects.all()
