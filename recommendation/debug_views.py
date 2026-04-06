from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from services.recommendation_engine_service import RecommendationEngineService
from utils.throttles import PerUserBurstRateThrottle


class RecommendationDebugAPIView(APIView):
    """
    Admin-only debug endpoint.
    GET /api/system/recommendation-debug/
    Returns the raw recommendation engine output for the authenticated user.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    throttle_classes = [PerUserBurstRateThrottle]

    def get(self, request, *args, **kwargs):
        result = RecommendationEngineService().recommend(user_id=request.user.id)
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)
