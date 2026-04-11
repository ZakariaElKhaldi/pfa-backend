from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StrategyExecution, StrategyRule
from .serializers import StrategyExecutionSerializer, StrategyRuleSerializer


class StrategyListCreateView(generics.ListCreateAPIView):
    serializer_class = StrategyRuleSerializer
    pagination_class = None  # Tests check len(resp.data) directly

    def get_queryset(self):
        return (
            StrategyRule.objects
            .filter(user=self.request.user)
            .prefetch_related("conditions", "actions", "tickers")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StrategyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StrategyRuleSerializer

    def get_queryset(self):
        return (
            StrategyRule.objects
            .filter(user=self.request.user)
            .prefetch_related("conditions", "actions", "tickers")
        )


class StrategyToggleView(APIView):
    def post(self, request, pk):
        try:
            rule = StrategyRule.objects.get(pk=pk, user=request.user)
        except StrategyRule.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        rule.is_active = not rule.is_active
        rule.save(update_fields=["is_active"])
        return Response(StrategyRuleSerializer(rule).data)


class StrategyExecutionListView(generics.ListAPIView):
    serializer_class = StrategyExecutionSerializer
    pagination_class = None

    def get_queryset(self):
        return StrategyExecution.objects.filter(
            rule__pk=self.kwargs["pk"], rule__user=self.request.user
        )
