from __future__ import annotations

import logging
from pathlib import Path

from django.db import transaction
from django_rq import job

from ai.inference import infer_semantic_label
from datasets.models import (
    Dataset,
    DatasetColumnProfile,
    DatasetProcessingJob,
    DatasetStatus,
    FileType,
    SemanticLabelSource,
    SheetStructureStatus,
)
from profiling.services import (
    PandasTabularReader,
    build_profile,
    is_structure_ambiguous,
    validate_with_pandera,
)
from profiling.models import ProfiledColumn, ProfilingRun
from semantic_mapping.models import SemanticMappingEntry, SemanticMappingRun

logger = logging.getLogger(__name__)


@job
def profile_dataset(dataset_id: int) -> None:
    dataset = Dataset.objects.select_related("workspace").get(pk=dataset_id)
    selected = dataset.sheets.filter(selected=True).first()
    job_rec = DatasetProcessingJob.objects.create(
        dataset=dataset,
        sheet=selected,
        job_type=DatasetProcessingJob.JobType.PROFILE,
        status=DatasetProcessingJob.JobStatus.QUEUED,
    )
    profiling_run = ProfilingRun.objects.create(
        dataset=dataset,
        sheet=selected,
        status=ProfilingRun.Status.QUEUED,
    )
    try:
        if not selected:
            raise ValueError("No sheet selected")
        if dataset.file_type not in (FileType.CSV, FileType.XLSX):
            raise ValueError("Unsupported file type for profiling")

        dataset.status = DatasetStatus.PROFILING
        dataset.error_message = ""
        dataset.save(update_fields=["status", "error_message"])
        job_rec.status = DatasetProcessingJob.JobStatus.RUNNING
        job_rec.save(update_fields=["status"])
        profiling_run.status = ProfilingRun.Status.RUNNING
        profiling_run.save(update_fields=["status"])

        path = Path(dataset.file.path)
        sheet_name = None if dataset.file_type == FileType.CSV else selected.name
        reader = PandasTabularReader()
        hr = selected.header_row_override
        df = reader.read_dataframe(path, dataset.file_type, sheet_name, header_row_1based=hr)
        sheet_analysis: dict = {}
        if dataset.file_type == FileType.XLSX and sheet_name:
            preview = reader.read_preview(path, dataset.file_type, sheet_name, rows=20, header_row_1based=hr)
            sheet_analysis = dict(preview.summary or {})
            eff = hr if hr is not None else sheet_analysis.get("detected_header_row", 1)
            sheet_analysis["detected_header_row"] = int(eff)
            sheet_analysis["header_row_source"] = "override" if hr is not None else "auto"
        elif dataset.file_type == FileType.CSV:
            eff = hr if hr is not None else 1
            sheet_analysis = {
                "detected_header_row": int(eff),
                "header_row_source": "override" if hr is not None else "auto",
            }
        ambiguous, amb_reasons = is_structure_ambiguous(sheet_analysis, df, dataset.file_type)
        if selected.structure_status == SheetStructureStatus.CONFIRMED:
            struct_status = SheetStructureStatus.CONFIRMED
        elif selected.header_row_override is not None:
            struct_status = SheetStructureStatus.CONFIRMED
        elif ambiguous:
            struct_status = SheetStructureStatus.NEEDS_REVIEW
        else:
            struct_status = SheetStructureStatus.AUTO_OK
        sheet_analysis["structure_ambiguity"] = {"ambiguous": ambiguous, "reasons": amb_reasons}
        result = build_profile(df, sheet_analysis=sheet_analysis)
        schema_validation = validate_with_pandera(df, schema_name="generic")

        with transaction.atomic():
            DatasetColumnProfile.objects.filter(sheet=selected).delete()
            for col in result.columns:
                DatasetColumnProfile.objects.create(
                    sheet=selected,
                    column_name=col.original_name,
                    normalized_name=col.normalized_name,
                    inferred_type=col.inferred_dtype,
                    null_ratio=col.null_ratio,
                    unique_ratio=col.unique_ratio,
                    sample_values=col.sample_values,
                    warnings=col.warnings,
                )
                ProfiledColumn.objects.create(
                    run=profiling_run,
                    sheet=selected,
                    original_name=col.original_name,
                    normalized_name=col.normalized_name,
                    inferred_dtype=col.inferred_dtype,
                    null_ratio=col.null_ratio,
                    unique_ratio=col.unique_ratio,
                    sample_values=col.sample_values,
                    warnings=col.warnings,
                )
            selected.row_count = result.rows_count
            selected.column_count = result.columns_count
            selected.analysis = {
                "detected_header_row": result.detected_header_row,
                "detected_data_start_row": result.detected_data_start_row,
                "sheet_analysis": result.sheet_analysis,
                "schema_validation": schema_validation,
            }
            selected.structure_status = struct_status
            selected.preview_ready = True
            selected.save(
                update_fields=["row_count", "column_count", "analysis", "preview_ready", "structure_status"]
            )

            dataset.status = DatasetStatus.PROFILED
            dataset.save(update_fields=["status"])
            job_rec.status = DatasetProcessingJob.JobStatus.SUCCEEDED
            job_rec.result = {"columns_count": result.columns_count, "rows_count": result.rows_count}
            job_rec.save(update_fields=["status", "result", "updated_at"])
            profiling_run.status = ProfilingRun.Status.SUCCEEDED
            profiling_run.summary = {
                "rows_count": result.rows_count,
                "columns_count": result.columns_count,
                "detected_header_row": result.detected_header_row,
            }
            profiling_run.save(update_fields=["status", "summary", "updated_at"])

        infer_semantic_columns.delay(dataset_id)
    except Exception as exc:
        logger.exception("profile_dataset failed dataset_id=%s", dataset_id)
        dataset.status = DatasetStatus.ERROR
        dataset.error_message = str(exc)
        dataset.save(update_fields=["status", "error_message"])
        job_rec.status = DatasetProcessingJob.JobStatus.FAILED
        job_rec.error_message = str(exc)
        job_rec.save(update_fields=["status", "error_message", "updated_at"])
        profiling_run.status = ProfilingRun.Status.FAILED
        profiling_run.error_message = str(exc)
        profiling_run.save(update_fields=["status", "error_message", "updated_at"])


@job
def infer_semantic_columns(dataset_id: int) -> None:
    dataset = Dataset.objects.get(pk=dataset_id)
    selected = dataset.sheets.filter(selected=True).first()
    if not selected:
        return
    job_rec = DatasetProcessingJob.objects.create(
        dataset=dataset,
        sheet=selected,
        job_type=DatasetProcessingJob.JobType.MAPPING,
        status=DatasetProcessingJob.JobStatus.RUNNING,
    )
    mapping_run = SemanticMappingRun.objects.create(
        dataset=dataset,
        sheet=selected,
        source=SemanticMappingRun.Source.AI,
    )
    for row in selected.column_profiles.all():
        label = infer_semantic_label(
            row.column_name or row.normalized_name,
            row.inferred_type,
            row.sample_values or [],
        )
        row.semantic_label = label
        row.semantic_label_source = SemanticLabelSource.AI
        row.save(update_fields=["semantic_label", "semantic_label_source"])
        SemanticMappingEntry.objects.create(
            run=mapping_run,
            sheet=selected,
            column_name=row.column_name,
            semantic_label=label,
            confidence=0.6,
            source=SemanticMappingRun.Source.AI,
        )

    dataset.status = DatasetStatus.MAPPING_READY
    dataset.save(update_fields=["status"])
    job_rec.status = DatasetProcessingJob.JobStatus.SUCCEEDED
    job_rec.result = {"mapped_columns": selected.column_profiles.count()}
    job_rec.save(update_fields=["status", "result", "updated_at"])
