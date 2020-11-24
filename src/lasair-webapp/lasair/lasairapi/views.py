from django.shortcuts import get_object_or_404, render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import ConeSerializer, StreamsSerializer, QuerySerializer 
from .serializers import LightcurvesSerializer, SherlockObjectsSerializer, SherlockPositionSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .query_auth import QueryAuthentication

def retcode(message):
    if 'error' in message: return status.HTTP_400_BAD_REQUEST
    else:                  return status.HTTP_200_OK

class ConeView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ConeSerializer(data=request.GET, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = ConeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StreamsView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, topic=None):
        data=request.GET.copy()
        if topic: 
            data['topic'] = topic
        serializer = StreamsSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None, topic=None):
        data=request.data.copy()
        if topic: 
            data['topic'] = topic
        serializer = StreamsSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class QueryView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = QuerySerializer(data=request.GET, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = QuerySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LightcurvesView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = LightcurvesSerializer(data=request.GET, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = LightcurvesSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SherlockObjectsView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = SherlockObjectsSerializer(data=request.GET, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = SherlockObjectsSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SherlockPositionView(APIView):
    authentication_classes = [TokenAuthentication, QueryAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = SherlockPositionSerializer(data=request.GET, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        serializer = SherlockPositionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            message = serializer.save()
            return Response(message, status=retcode(message))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
