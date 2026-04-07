"""
``TableReadArtifact`` ORM・015 §7.4 最小永続化のテスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_table_read_artifact_model.py
"""

from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from table_intelligence.models import AnalysisJob, JobStatus, TableReadArtifact, TableScope
from table_intelligence.serializers import TableReadArtifactSerializer
from table_intelligence.services import (
    get_latest_table_read_artifact_for_table,
    table_read_artifact_to_api_dict,
)


@pytest.fixture
def ra_job(user):
    return AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )


@pytest.fixture
def ra_table(ra_job):
    return TableScope.objects.create(job=ra_job, workspace_id="ws-ti")


@pytest.mark.django_db
def test_table_read_artifact_defaults_and_json(ra_table, ra_job):
    cells = {"R0C0": {"value": "x"}}
    merges = [{"anchor_row": 0, "anchor_col": 0, "height": 1, "width": 2}]
    warnings = [{"code": "TI_READ_TEST", "message": "m", "scope": "table"}]
    row = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells=cells,
        merges=merges,
        parse_warnings=warnings,
    )
    row.refresh_from_db()
    assert row.artifact_version == 1
    assert row.is_latest is True
    assert row.cells == cells
    assert row.merges == merges
    assert row.parse_warnings == warnings
    assert row.workspace_id == "ws-ti"


@pytest.mark.django_db
def test_table_read_artifact_job_nullable(ra_table):
    row = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=None,
        cells={},
        merges=[],
        parse_warnings=[],
    )
    assert row.job_id is None


@pytest.mark.django_db
def test_unique_latest_per_table(ra_table, ra_job):
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={},
        merges=[],
        parse_warnings=[],
        is_latest=True,
    )
    with pytest.raises(IntegrityError):
        TableReadArtifact.objects.create(
            workspace_id="ws-ti",
            table=ra_table,
            job=ra_job,
            cells={},
            merges=[],
            parse_warnings=[],
            is_latest=True,
        )


@pytest.mark.django_db
def test_multiple_non_latest_allowed(ra_table, ra_job):
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={},
        merges=[],
        parse_warnings=[],
        is_latest=False,
        artifact_version=1,
    )
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={},
        merges=[],
        parse_warnings=[],
        is_latest=False,
        artifact_version=2,
    )
    assert TableReadArtifact.objects.filter(table=ra_table).count() == 2


@pytest.mark.django_db
def test_get_latest_table_read_artifact_helper(ra_table, ra_job):
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={"old": True},
        merges=[],
        parse_warnings=[],
        is_latest=False,
    )
    latest = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={"new": True},
        merges=[],
        parse_warnings=[],
        is_latest=True,
    )
    found = get_latest_table_read_artifact_for_table(ra_table)
    assert found is not None
    assert found.artifact_id == latest.artifact_id


@pytest.mark.django_db
def test_table_read_artifact_api_dict_and_serializer(ra_table, ra_job):
    row = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ra_table,
        job=ra_job,
        cells={"a": 1},
        merges=[{"m": 1}],
        parse_warnings=[{"w": 1}],
    )
    d = table_read_artifact_to_api_dict(row)
    assert d["artifact_id"] == str(row.artifact_id)
    assert d["table_id"] == str(ra_table.table_id)
    assert d["cells"] == {"a": 1}
    assert d["merges"][0] == {"m": 1}

    ser = TableReadArtifactSerializer(row)
    assert ser.data["cells"] == {"a": 1}
    assert uuid.UUID(str(ser.data["artifact_id"])) == row.artifact_id
