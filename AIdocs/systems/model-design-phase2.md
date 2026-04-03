# Model Design Phase 2

## Dataset
- workspace
- uploaded_by
- name
- file
- file_type
- status
- created_at

## DatasetFile
- dataset (1:1)
- original_name
- mime_type
- size_bytes
- storage_path

## DatasetSheet
- dataset
- name
- order
- selected

## DatasetColumnProfile
- sheet
- column_name
- normalized_name
- inferred_type
- null_ratio
- unique_ratio
- sample_values
- warnings
- semantic_label
- semantic_label_source

## DatasetPreview
- dataset
- sheet
- columns
- rows
- summary

## DatasetProcessingJob
- dataset
- sheet
- job_type (preview/profile/mapping)
- status (queued/running/succeeded/failed)
- payload/result/error_message

## ProfilingRun / ProfiledColumn
- profiling 実行履歴と列スナップショットの分離保持

## SemanticMappingRun / SemanticMappingEntry
- AI推定とuser修正の履歴保持
