from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SignalSnapshot, AlertFlag
from .serializers import SignalSnapshotSerializer, AlertFlagSerializer


class TickerSignalView(APIView):
    def get(self, request, symbol):
        snap = SignalSnapshot.objects.filter(ticker__symbol=symbol).first()
        if snap is None:
            return Response({"detail": "No signal yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SignalSnapshotSerializer(snap).data)


class AlertListView(generics.ListAPIView):
    serializer_class = AlertFlagSerializer

    def get_queryset(self):
        return AlertFlag.objects.filter(resolved=False).order_by("-created_at")


class AlertResolveView(APIView):
    def patch(self, request, pk):
        try:
            alert = AlertFlag.objects.get(pk=pk)
        except AlertFlag.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.resolved = True
        alert.save(update_fields=["resolved"])
        return Response(AlertFlagSerializer(alert).data)
