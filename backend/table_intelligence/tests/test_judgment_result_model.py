"""
``JudgmentResult`` ORM・015 §7.5 最小永続化のテスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_judgment_result_model.py
"""

from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from table_intelligence.models import (
    AnalysisJob,
    JobStatus,
    JudgmentDecision,
    JudgmentResult,
    TI_TABLE_UNKNOWN,
    TableScope,
)
from table_intelligence.serializers import JudgmentResultSerializer
from table_intelligence.services import (
    get_latest_judgment_result_for_table,
    judgment_result_to_judgment_api_dict,
)


@pytest.fixture
def j_job(user):
    return AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )


@pytest.fixture
def j_table(j_job):
    return TableScope.objects.create(job=j_job, workspace_id="ws-ti")


@pytest.mark.django_db
def test_judgment_result_defaults_and_save(j_table, j_job):
    ev = [{"rule_id": "J2-TEST-001", "conclusion": "taxonomy=LIST_DETAIL"}]
    row = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.AUTO_ACCEPT,
        evidence=ev,
    )
    row.refresh_from_db()
    assert row.taxonomy_code == TI_TABLE_UNKNOWN
    assert row.artifact_version == 1
    assert row.is_latest is True
    assert row.decision == JudgmentDecision.AUTO_ACCEPT
    assert row.evidence == ev
    assert row.workspace_id == "ws-ti"
    assert row.table_id == j_table.table_id


@pytest.mark.django_db
def test_judgment_result_job_nullable(j_table):
    row = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=None,
        decision=JudgmentDecision.NEEDS_REVIEW,
        evidence=[{"rule_id": "x", "conclusion": "y"}],
    )
    assert row.job_id is None


@pytest.mark.django_db
def test_unique_latest_per_table(j_table, j_job):
    JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        evidence=[{"rule_id": "a", "conclusion": "b"}],
        is_latest=True,
    )
    with pytest.raises(IntegrityError):
        JudgmentResult.objects.create(
            workspace_id="ws-ti",
            table=j_table,
            job=j_job,
            decision=JudgmentDecision.REJECT,
            evidence=[{"rule_id": "c", "conclusion": "d"}],
            is_latest=True,
        )


@pytest.mark.django_db
def test_multiple_non_latest_allowed(j_table, j_job):
    JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        evidence=[],
        is_latest=False,
        artifact_version=1,
    )
    JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.AUTO_ACCEPT,
        evidence=[],
        is_latest=False,
        artifact_version=2,
    )
    assert JudgmentResult.objects.filter(table=j_table).count() == 2


@pytest.mark.django_db
def test_get_latest_judgment_helper(j_table, j_job):
    JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        evidence=[],
        is_latest=False,
    )
    latest = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.AUTO_ACCEPT,
        evidence=[{"rule_id": "last", "conclusion": "ok"}],
        is_latest=True,
    )
    found = get_latest_judgment_result_for_table(j_table)
    assert found is not None
    assert found.judgment_id == latest.judgment_id


@pytest.mark.django_db
def test_judgment_api_dict_and_serializer(j_table, j_job):
    row = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=j_table,
        job=j_job,
        decision=JudgmentDecision.REJECT,
        taxonomy_code="TI_TABLE_LIST_DETAIL",
        evidence=[{"rule_id": "r", "conclusion": "c"}],
    )
    d = judgment_result_to_judgment_api_dict(row)
    assert d["judgment_id"] == str(row.judgment_id)
    assert d["table_id"] == str(j_table.table_id)
    assert d["decision"] == JudgmentDecision.REJECT
    assert d["taxonomy_code"] == "TI_TABLE_LIST_DETAIL"
    assert d["evidence"][0]["rule_id"] == "r"

    ser = JudgmentResultSerializer(row)
    assert ser.data["decision"] == JudgmentDecision.REJECT
    assert uuid.UUID(str(ser.data["table_id"])) == j_table.table_id
