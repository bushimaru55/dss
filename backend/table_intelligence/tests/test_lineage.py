"""
artifact_relation / lineage（rerun → materialize 後の旧→新 edge）。
"""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

from table_intelligence.models import AnalysisJob, ArtifactRelation, JobStatus, JudgmentResult, TableReadArtifact
from table_intelligence.services import (
    LINEAGE_RELATION_JOB_RERUN,
    LINEAGE_RELATION_REVIEW_RERUN,
    ARTIFACT_TYPE_DATASET,
    ARTIFACT_TYPE_JUDGMENT,
    ARTIFACT_TYPE_JOB,
    ARTIFACT_TYPE_METADATA,
    ARTIFACT_TYPE_READ_ARTIFACT,
    ARTIFACT_TYPE_SESSION,
    execute_mvp_pipeline_for_job,
)


@pytest.mark.django_db
def test_job_rerun_creates_artifact_relations(auth_client, user):
    base = reverse("ti-table-analysis-job-create")
    r1 = auth_client.post(base, {"workspace_id": "ws-1"}, format="json")
    assert r1.status_code == 202
    jid1 = uuid.UUID(r1.data["job_id"])
    execute_mvp_pipeline_for_job(jid1)
    d1 = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid1})
    )
    old_meta = d1.data["artifact_refs"]["metadata_id"]
    old_ds = d1.data["artifact_refs"]["dataset_id"]

    r2 = auth_client.post(
        reverse("ti-table-analysis-job-rerun", kwargs={"job_id": jid1}),
        {},
        format="json",
    )
    assert r2.status_code == 201
    jid2 = uuid.UUID(r2.data["job_id"])
    execute_mvp_pipeline_for_job(jid2)

    rels = ArtifactRelation.objects.filter(
        workspace_id="ws-1", relation_type=LINEAGE_RELATION_JOB_RERUN
    )
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_METADATA,
        from_artifact_id=old_meta,
        to_artifact_type=ARTIFACT_TYPE_METADATA,
    ).exists()
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_DATASET,
        from_artifact_id=old_ds,
        to_artifact_type=ARTIFACT_TYPE_DATASET,
    ).exists()
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_JOB,
        from_artifact_id=str(jid1),
        to_artifact_type=ARTIFACT_TYPE_JOB,
        to_artifact_id=str(jid2),
        context_job_id=jid2,
    ).exists()


@pytest.mark.django_db
def test_review_rerun_creates_artifact_relations(auth_client, user):
    r0 = auth_client.post(
        reverse("ti-table-analysis-job-create"),
        {"workspace_id": "ws-1"},
        format="json",
    )
    assert r0.status_code == 202
    jid = uuid.UUID(r0.data["job_id"])
    execute_mvp_pipeline_for_job(jid)
    det = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid})
    )
    refs = det.data["artifact_refs"]
    session_id = refs["session_id"]
    old_meta = refs["metadata_id"]
    old_ds = refs["dataset_id"]

    rr = auth_client.post(
        reverse("ti-review-session-rerun", kwargs={"session_id": session_id}),
        {},
        format="json",
    )
    assert rr.status_code == 202
    new_jid = uuid.UUID(rr.data["job_id"])
    execute_mvp_pipeline_for_job(new_jid)

    rels = ArtifactRelation.objects.filter(
        workspace_id="ws-1", relation_type=LINEAGE_RELATION_REVIEW_RERUN
    )
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_METADATA,
        from_artifact_id=old_meta,
        to_artifact_type=ARTIFACT_TYPE_METADATA,
    ).exists()
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_DATASET,
        from_artifact_id=old_ds,
        to_artifact_type=ARTIFACT_TYPE_DATASET,
    ).exists()
    assert rels.filter(
        from_artifact_type=ARTIFACT_TYPE_SESSION,
        from_artifact_id=session_id,
        to_artifact_type=ARTIFACT_TYPE_SESSION,
    ).exists()


@pytest.mark.django_db
def test_lineage_skipped_when_prior_workspace_mismatch(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-1",
        request_payload={
            "lineage": {
                "relation_type": LINEAGE_RELATION_JOB_RERUN,
                "prior_workspace_id": "ws-2",
                "source_job_id": str(uuid.uuid4()),
                "prior_metadata_id": str(uuid.uuid4()),
                "prior_dataset_id": str(uuid.uuid4()),
            }
        },
        status=JobStatus.PENDING,
        current_stage="queued",
        requested_by=user,
    )
    execute_mvp_pipeline_for_job(job.job_id)
    assert ArtifactRelation.objects.filter(workspace_id="ws-1").count() == 0


@pytest.mark.django_db
def test_job_rerun_demotes_prior_judgment_and_decision_api(auth_client, user):
    base = reverse("ti-table-analysis-job-create")
    r1 = auth_client.post(base, {"workspace_id": "ws-1"}, format="json")
    assert r1.status_code == 202
    jid1 = uuid.UUID(r1.data["job_id"])
    execute_mvp_pipeline_for_job(jid1)
    det1 = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid1})
    )
    tid1 = det1.data["artifact_refs"]["table_id"]
    assert JudgmentResult.objects.filter(table_id=tid1, is_latest=True).count() == 1
    j1 = JudgmentResult.objects.get(table_id=tid1, is_latest=True)
    ra1 = TableReadArtifact.objects.get(table_id=tid1, is_latest=True)
    url_d1 = reverse("ti-table-decision", kwargs={"table_id": tid1})
    assert auth_client.get(url_d1).status_code == 200
    url_r1 = reverse("ti-table-read-artifact", kwargs={"table_id": tid1})
    assert auth_client.get(url_r1).status_code == 200

    r2 = auth_client.post(
        reverse("ti-table-analysis-job-rerun", kwargs={"job_id": jid1}),
        {},
        format="json",
    )
    assert r2.status_code == 201
    jid2 = uuid.UUID(r2.data["job_id"])
    execute_mvp_pipeline_for_job(jid2)
    det2 = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid2})
    )
    tid2 = det2.data["artifact_refs"]["table_id"]
    assert str(tid1) != str(tid2)

    j1.refresh_from_db()
    assert j1.is_latest is False
    j2 = JudgmentResult.objects.get(table_id=tid2, is_latest=True)
    assert j2.is_latest is True

    ra1.refresh_from_db()
    assert ra1.is_latest is False
    ra2 = TableReadArtifact.objects.get(table_id=tid2, is_latest=True)

    assert auth_client.get(url_d1).status_code == 404
    assert auth_client.get(url_r1).status_code == 404
    url_d2 = reverse("ti-table-decision", kwargs={"table_id": tid2})
    res2 = auth_client.get(url_d2)
    assert res2.status_code == 200
    assert res2.data["judgment_id"] == str(j2.judgment_id)
    url_r2 = reverse("ti-table-read-artifact", kwargs={"table_id": tid2})
    rres = auth_client.get(url_r2)
    assert rres.status_code == 200
    assert rres.data["artifact_id"] == str(ra2.artifact_id)

    assert ArtifactRelation.objects.filter(
        workspace_id="ws-1",
        relation_type=LINEAGE_RELATION_JOB_RERUN,
        from_artifact_type=ARTIFACT_TYPE_JUDGMENT,
        from_artifact_id=str(j1.judgment_id),
        to_artifact_type=ARTIFACT_TYPE_JUDGMENT,
        to_artifact_id=str(j2.judgment_id),
        context_job_id=jid2,
    ).exists()
    assert ArtifactRelation.objects.filter(
        workspace_id="ws-1",
        relation_type=LINEAGE_RELATION_JOB_RERUN,
        from_artifact_type=ARTIFACT_TYPE_READ_ARTIFACT,
        from_artifact_id=str(ra1.artifact_id),
        to_artifact_type=ARTIFACT_TYPE_READ_ARTIFACT,
        to_artifact_id=str(ra2.artifact_id),
        context_job_id=jid2,
    ).exists()


@pytest.mark.django_db
def test_review_rerun_demotes_prior_judgment_and_edge(auth_client, user):
    r0 = auth_client.post(
        reverse("ti-table-analysis-job-create"),
        {"workspace_id": "ws-1"},
        format="json",
    )
    assert r0.status_code == 202
    jid = uuid.UUID(r0.data["job_id"])
    execute_mvp_pipeline_for_job(jid)
    det = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid})
    )
    refs = det.data["artifact_refs"]
    tid1 = refs["table_id"]
    j1 = JudgmentResult.objects.get(table_id=tid1, is_latest=True)
    ra1 = TableReadArtifact.objects.get(table_id=tid1, is_latest=True)

    rr = auth_client.post(
        reverse("ti-review-session-rerun", kwargs={"session_id": refs["session_id"]}),
        {},
        format="json",
    )
    assert rr.status_code == 202
    new_jid = uuid.UUID(rr.data["job_id"])
    execute_mvp_pipeline_for_job(new_jid)
    det2 = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": new_jid})
    )
    tid2 = det2.data["artifact_refs"]["table_id"]
    assert str(tid1) != str(tid2)

    j1.refresh_from_db()
    assert j1.is_latest is False
    j2 = JudgmentResult.objects.get(table_id=tid2, is_latest=True)

    ra1.refresh_from_db()
    assert ra1.is_latest is False
    ra2 = TableReadArtifact.objects.get(table_id=tid2, is_latest=True)

    assert ArtifactRelation.objects.filter(
        workspace_id="ws-1",
        relation_type=LINEAGE_RELATION_REVIEW_RERUN,
        from_artifact_type=ARTIFACT_TYPE_JUDGMENT,
        from_artifact_id=str(j1.judgment_id),
        to_artifact_type=ARTIFACT_TYPE_JUDGMENT,
        to_artifact_id=str(j2.judgment_id),
        context_job_id=new_jid,
    ).exists()
    assert ArtifactRelation.objects.filter(
        workspace_id="ws-1",
        relation_type=LINEAGE_RELATION_REVIEW_RERUN,
        from_artifact_type=ARTIFACT_TYPE_READ_ARTIFACT,
        from_artifact_id=str(ra1.artifact_id),
        to_artifact_type=ARTIFACT_TYPE_READ_ARTIFACT,
        to_artifact_id=str(ra2.artifact_id),
        context_job_id=new_jid,
    ).exists()
