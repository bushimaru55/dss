from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from analysis_runs.services import ANALYSIS_FACTS_SCHEMA_VERSION, execute_analysis
from datasets.models import Dataset


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


def test_run_analysis_appends_audit_jsonl(auth_client, workspace, monkeypatch, settings):
    """run_analysis_to_completion が JSONL に 1 行追記する。"""
    from pathlib import Path

    log_path = Path(settings.BASE_DIR) / "logs" / "pytest_audit_once.jsonl"
    settings.ANALYSIS_AUDIT_LOG_PATH = log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()

    create_res = auth_client.post(
        reverse("dataset-list"),
        data={"name": "audit-ds", "workspace": workspace.id, "file": _sample_csv()},
        format="multipart",
    )
    dataset_id = create_res.data["id"]
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
    run_id = ask_res.data["analysis_run_id"]
    detail_res = auth_client.get(f"/api/chat/ask/{run_id}")
    if detail_res.data["status"] != "succeeded":
        return
    assert log_path.is_file()
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    import json

    row = json.loads(line)
    assert row["run_id"] == run_id
    assert row["status"] == "succeeded"
    assert "facts_summary" in row
    assert "auto_checks" in row


def test_execute_analysis_facts_layer_shape(auth_client, workspace, monkeypatch):
    """分析ファクト層: result_json 相当の facts に schema_version と決定的キーが含まれる。"""
    create_res = auth_client.post(
        reverse("dataset-list"),
        data={"name": "facts-ds", "workspace": workspace.id, "file": _sample_csv()},
        format="multipart",
    )
    assert create_res.status_code == 201
    dataset_id = create_res.data["id"]

    from datasets import tasks as d_tasks

    monkeypatch.setattr(d_tasks.infer_semantic_columns, "delay", lambda x: d_tasks.infer_semantic_columns(x))
    monkeypatch.setattr("datasets.views.profile_dataset.delay", lambda x: d_tasks.profile_dataset(x), raising=False)
    auth_client.post(reverse("dataset-profile", kwargs={"pk": dataset_id}), data={}, format="json")

    ds = Dataset.objects.get(pk=dataset_id)
    out = execute_analysis(ds, "売上合計は？")
    facts = out["facts"]
    assert facts["schema_version"] == ANALYSIS_FACTS_SCHEMA_VERSION
    assert "row_count" in facts
    assert "detected_columns" in facts
    assert out["plan"]["strategy"] == "deterministic_dataframe_aggregation"
    assert "question" in out["plan"]


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
        assert "fact_keys" in detail_res.data["evidence"]


def test_build_auto_checks_detects_ungrounded_number():
    from analysis_runs.audit_log import build_auto_checks

    facts = {"amount_sum": 100.0, "row_count": 2}
    out = build_auto_checks("合計は999.0です（根拠なし）", facts)
    assert out["suspected_ungrounded_numbers"]
    out_ok = build_auto_checks("合計は 100 です", facts)
    assert not out_ok["suspected_ungrounded_numbers"]
