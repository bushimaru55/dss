from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rag.serializers import RagIndexSerializer, RagSearchSerializer
from rag.services import collect_aidocs_documents, index_documents, search_chunks


class RagIndexView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # manual docs indexing
        if request.data.get("auto_aidocs"):
            docs = collect_aidocs_documents(request.data.get("aidocs_dir"))
            count = index_documents(docs, source_type="aidocs", replace_scope="aidocs")
            return Response({"ok": True, "count": count})

        ser = RagIndexSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = index_documents(
            ser.validated_data["documents"],
            source_type=ser.validated_data.get("source_type", "manual"),
            replace_scope=ser.validated_data.get("replace_scope") or None,
        )
        return Response({"ok": True, "count": count})


class RagSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = RagSearchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        items = search_chunks(
            ser.validated_data["query"],
            limit=ser.validated_data.get("limit", 5),
        )
        return Response({"items": items})
