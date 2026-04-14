import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse


def _sample_csv() -> SimpleUploadedFile:
    content = (
        "order_date,customer,amount,status\n"
        "2026-03-01,Acme,1200,open\n"
        "2026-03-02,Bravo,980,closed\n"
    ).encode("utf-8")
    return SimpleUploadedFile("ui_sample.csv", content, content_type="text/csv")


def test_enduser_ui_upload_and_candidate_flow(db, user, workspace, monkeypatch):
    from datasets import tasks as d_tasks

    monkeypatch.setattr(d_tasks.infer_semantic_columns, "delay", lambda x: d_tasks.infer_semantic_columns(x))

    c = Client()
    assert c.login(username="tester", password="tester")

    new_res = c.post(
        reverse("enduser-dataset-new"),
        data={
            "name": "ui-ds",
            "workspace": workspace.id,
            "file": _sample_csv(),
        },
    )
    assert new_res.status_code == 302

    # アップロード直後は /datasets/<id>/import/ へ飛ぶ。prepare_analysis は詳細 URL のみ。
    m = re.search(r"/datasets/(\d+)", new_res["Location"])
    assert m
    detail_url = reverse("enduser-dataset-detail", kwargs={"dataset_id": int(m.group(1))})
    run_res = c.post(detail_url, data={"action": "prepare_analysis"})
    assert run_res.status_code == 302

    page = c.get(detail_url)
    assert page.status_code == 200
    assert "分析候補" in page.content.decode("utf-8")
