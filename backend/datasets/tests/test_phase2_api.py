from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from datasets import tasks
from datasets.models import DatasetColumnProfile, SemanticLabelSource


def _sample_csv() -> SimpleUploadedFile:
    content = (
        "order_date,customer,amount,status,assignee\n"
        "2026-03-01,Acme,1200,open,Sato\n"
        "2026-03-02,Bravo,980,closed,Suzuki\n"
        ",Charlie,1500,open,Tanaka\n"
    ).encode("utf-8")
    return SimpleUploadedFile("sample.csv", content, content_type="text/csv")


def _run_profile_and_mapping_sync(monkeypatch):
    def inline_infer(dataset_id: int):
        return tasks.infer_semantic_columns(dataset_id)

    monkeypatch.setattr(tasks.infer_semantic_columns, "delay", inline_infer)

    def inline_profile(dataset_id: int):
        return tasks.profile_dataset(dataset_id)

    monkeypatch.setattr("datasets.views.profile_dataset.delay", inline_profile, raising=False)


def test_dataset_create_returns_detail_payload(auth_client, workspace):
    url = reverse("dataset-list")
    res = auth_client.post(
        url,
        data={
            "name": "phase2-sample",
            "workspace": workspace.id,
            "file": _sample_csv(),
        },
        format="multipart",
    )

    assert res.status_code == 201
    assert "id" in res.data
    assert res.data["status"] == "uploaded"
    assert len(res.data["sheets"]) == 1
    assert res.data["sheets"][0]["name"] == "data"
    assert res.data["file_record"]["original_name"] == "sample.csv"


def test_phase2_api_e2e_upload_profile_semantic(auth_client, workspace, monkeypatch):
    _run_profile_and_mapping_sync(monkeypatch)

    create_res = auth_client.post(
        reverse("dataset-list"),
        data={
            "name": "phase2-e2e",
            "workspace": workspace.id,
            "file": _sample_csv(),
        },
        format="multipart",
    )
    assert create_res.status_code == 201
    dataset_id = create_res.data["id"]
    sheet_id = create_res.data["sheets"][0]["id"]

    select_res = auth_client.post(
        reverse("dataset-select-sheet", kwargs={"pk": dataset_id}),
        data={"sheet_id": sheet_id},
        format="json",
    )
    assert select_res.status_code == 200

    profile_enqueue_res = auth_client.post(
        reverse("dataset-profile", kwargs={"pk": dataset_id}),
        data={},
        format="json",
    )
    assert profile_enqueue_res.status_code == 202
    assert profile_enqueue_res.data["enqueued"] is True

    profile_res = auth_client.get(reverse("dataset-profile", kwargs={"pk": dataset_id}))
    assert profile_res.status_code == 200
    assert profile_res.data["sheet"]["row_count"] == 3
    assert profile_res.data["sheet"]["column_count"] == 5

    cols = {c["column_name"]: c for c in profile_res.data["columns"]}
    assert cols["order_date"]["inferred_type"] == "date"
    assert cols["amount"]["inferred_type"] == "number"
    assert cols["order_date"]["null_ratio"] == 1 / 3
    assert cols["amount"]["semantic_label_source"] == "ai"

    sem_res = auth_client.post(
        reverse("dataset-semantic-mapping", kwargs={"pk": dataset_id}),
        data={
            "columns": [
                {"column_name": "amount", "semantic_label": "amount"},
                {"column_name": "status", "semantic_label": "status"},
            ]
        },
        format="json",
    )
    assert sem_res.status_code == 200
    assert sem_res.data["ok"] is True

    updated = DatasetColumnProfile.objects.filter(
        sheet_id=sheet_id,
        column_name__in=["amount", "status"],
    ).values_list("column_name", "semantic_label_source")
    updated_map = {name: source for name, source in updated}
    assert updated_map["amount"] == SemanticLabelSource.USER
    assert updated_map["status"] == SemanticLabelSource.USER


def test_suggestions_generation(auth_client, workspace, monkeypatch):
    _run_profile_and_mapping_sync(monkeypatch)

    create_res = auth_client.post(
        reverse("dataset-list"),
        data={
            "name": "phase3-suggestions",
            "workspace": workspace.id,
            "file": _sample_csv(),
        },
        format="multipart",
    )
    dataset_id = create_res.data["id"]

    auth_client.post(reverse("dataset-profile", kwargs={"pk": dataset_id}), data={}, format="json")

    gen_res = auth_client.post(
        reverse("dataset-generate-suggestions", kwargs={"pk": dataset_id}),
        data={},
        format="json",
    )
    assert gen_res.status_code == 200
    assert gen_res.data["ok"] is True
    assert gen_res.data["count"] >= 1

    list_res = auth_client.get(reverse("dataset-list-suggestions", kwargs={"pk": dataset_id}))
    assert list_res.status_code == 200
    assert len(list_res.data["items"]) >= 1


def test_preview_and_semantic_generate_endpoints(auth_client, workspace, monkeypatch):
    _run_profile_and_mapping_sync(monkeypatch)
    create_res = auth_client.post(
        reverse("dataset-list"),
        data={
            "name": "preprocess-preview",
            "workspace": workspace.id,
            "file": _sample_csv(),
        },
        format="multipart",
    )
    dataset_id = create_res.data["id"]

    sheets_res = auth_client.get(reverse("dataset-sheets", kwargs={"pk": dataset_id}))
    assert sheets_res.status_code == 200
    assert len(sheets_res.data["items"]) == 1

    preview_res = auth_client.get(reverse("dataset-preview", kwargs={"pk": dataset_id}) + "?rows=2")
    assert preview_res.status_code == 200
    assert len(preview_res.data["rows"]) == 2
    assert "columns" in preview_res.data

    auth_client.post(reverse("dataset-profile", kwargs={"pk": dataset_id}), data={}, format="json")
    gen_res = auth_client.post(reverse("dataset-semantic-mapping-generate", kwargs={"pk": dataset_id}), data={}, format="json")
    assert gen_res.status_code == 200
    assert gen_res.data["ok"] is True

    mapping_list = auth_client.get(reverse("dataset-semantic-mapping", kwargs={"pk": dataset_id}))
    assert mapping_list.status_code == 200
    assert len(mapping_list.data["items"]) >= 1
