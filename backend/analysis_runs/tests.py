from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


def _sample_csv() -> SimpleUploadedFile:
    content = (
        "order_date,customer,amount,status\n"
        "2026-03-01,Acme,1200,open\n"
        "2026-03-02,Bravo,980,closed\n"
    ).encode("utf-8")
    return SimpleUploadedFile("chat_sample.csv", content, content_type="text/csv")


def test_chat_ask_flow(auth_client, workspace, monkeypatch):
    # create dataset
    create_res = auth_client.post(
        reverse("dataset-list"),
        data={"name": "chat-ds", "workspace": workspace.id, "file": _sample_csv()},
        format="multipart",
    )
    dataset_id = create_res.data["id"]

    # make profiling/mapping run synchronously so semantic labels exist
    from datasets import tasks as d_tasks

    monkeypatch.setattr(d_tasks.infer_semantic_columns, "delay", lambda x: d_tasks.infer_semantic_columns(x))
    monkeypatch.setattr("datasets.views.profile_dataset.delay", lambda x: d_tasks.profile_dataset(x), raising=False)
    auth_client.post(reverse("dataset-profile", kwargs={"pk": dataset_id}), data={}, format="json")

    from analysis_runs import tasks as a_tasks

    monkeypatch.setattr("analysis_runs.views.run_analysis_job.delay", lambda x: a_tasks.run_analysis_job(x), raising=False)

    ask_res = auth_client.post(
        "/api/chat/ask",
        data={"dataset_id": dataset_id, "question": "売上合計を教えて"},
        format="json",
    )
    assert ask_res.status_code == 202

    run_id = ask_res.data["analysis_run_id"]
    detail_res = auth_client.get(f"/api/chat/ask/{run_id}")
    assert detail_res.status_code == 200
    assert detail_res.data["status"] in ["succeeded", "running", "queued"]
    if detail_res.data["status"] == "succeeded":
        assert detail_res.data["answer"]


def test_chat_ask_with_rag_evidence(auth_client, workspace, monkeypatch):
    # seed rag
    auth_client.post(
        "/api/rag/index",
        data={
            "source_type": "manual",
            "replace_scope": "chat_seed",
            "documents": [
                {
                    "title": "分析ルール",
                    "source_id": "chat_seed",
                    "content": "売上分析では amount 列を優先します。",
                }
            ],
        },
        format="json",
    )

    from analysis_runs import tasks as a_tasks
    monkeypatch.setattr("analysis_runs.views.run_analysis_job.delay", lambda x: a_tasks.run_analysis_job(x), raising=False)

    create_res = auth_client.post(
        reverse("dataset-list"),
        data={"name": "chat-rag", "workspace": workspace.id, "file": _sample_csv()},
        format="multipart",
    )
    dataset_id = create_res.data["id"]

    from datasets import tasks as d_tasks
    monkeypatch.setattr(d_tasks.infer_semantic_columns, "delay", lambda x: d_tasks.infer_semantic_columns(x))
    monkeypatch.setattr("datasets.views.profile_dataset.delay", lambda x: d_tasks.profile_dataset(x), raising=False)
    auth_client.post(reverse("dataset-profile", kwargs={"pk": dataset_id}), data={}, format="json")

    ask_res = auth_client.post("/api/chat/ask", data={"dataset_id": dataset_id, "question": "売上を分析して"}, format="json")
    run_id = ask_res.data["analysis_run_id"]
    detail_res = auth_client.get(f"/api/chat/ask/{run_id}")
    assert detail_res.status_code == 200
    if detail_res.data["status"] == "succeeded":
        assert "rag_items" in detail_res.data["evidence"]
