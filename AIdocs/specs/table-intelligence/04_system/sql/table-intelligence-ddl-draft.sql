-- title: Table Intelligence DDL Draft
-- version: 0.1.0-draft
-- last_updated: 2026-04-07
-- references:
--   SPEC-TI-015 (DB 永続化の正本)
--   SPEC-TI-014 (API 契約; 物理名で逆流上書きしない)
--   SPEC-TI-006 (DTO / 列挙の意味の正本)
-- position: PostgreSQL 想定の初期 DDL 叩き台（実装マイグレーションで確定）
-- notes:
--   - API の evaluation_ref / suggestion_run_ref は DB 列 evaluation_id / suggestion_run_id と同一キー空間（015 §5.2）。
--   - 002 の decision と 011 の decision_recommendation は別列（judgment_result vs confidence_evaluation）。
--   - session_id のみ採用（review_session_id は定義しない）。
-- TODO: 列挙の完全 CHECK、RLS、パーティション、トリガは次工程。

-- =============================================================================
-- 0. extensions / notes
-- =============================================================================
-- 初版は必須拡張なし（主キーはアプリ発行の text 前提）。必要になったら拡張をマイグレーションで追加。

-- =============================================================================
-- 1. job tables
-- =============================================================================

CREATE TABLE analysis_job (
  job_id              text PRIMARY KEY,
  workspace_id        text NOT NULL,
  status              text NOT NULL,
  kind                text NOT NULL,
  table_id            text,
  source_id           text,
  document_id         text,
  idempotency_key     text,
  error_code          text,
  -- ジョブ完了時スナップショット（値は evaluation_id / suggestion_run_id と同一文字列; 015 §7.1）
  evaluation_ref      text,
  suggestion_run_ref  text,
  input_parameters    jsonb,
  created_at          timestamptz NOT NULL DEFAULT now(),
  completed_at        timestamptz,
  CONSTRAINT analysis_job_status_chk CHECK (status IN (
    'PENDING', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'
  )),
  CONSTRAINT analysis_job_kind_chk CHECK (kind IN (
    'READ', 'JUDGE', 'NORMALIZE', 'META', 'REVIEW_RERUN', 'SUGGESTION', 'EVALUATION', 'FULL_PIPELINE'
  ))
);
-- TODO: status/kind の完全列挙は SPEC-TI-006 JobRun と突合して確定。

COMMENT ON TABLE analysis_job IS '014 実行 API のジョブ単位。成果物テーブルとは分離（015 §7.1）。';
COMMENT ON COLUMN analysis_job.evaluation_ref IS 'API 名。DB 上の confidence_evaluation.evaluation_id と同値（014/015）。';
COMMENT ON COLUMN analysis_job.suggestion_run_ref IS 'API 名。DB 上の suggestion_set.suggestion_run_id と同値。';

-- table_id は table_scope 作成後に FK を追加（§1b）。

-- =============================================================================
-- 2. artifact tables
-- =============================================================================

CREATE TABLE table_scope (
  table_id      text PRIMARY KEY,
  workspace_id  text NOT NULL,
  source_id     text,
  document_id   text,
  sheet_id      text,
  bbox          jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE table_scope IS 'table_id の安定アンカー（001 観測対象コンテナ; 015 §7.3）。';

ALTER TABLE analysis_job
  ADD CONSTRAINT analysis_job_table_id_fkey
  FOREIGN KEY (table_id) REFERENCES table_scope (table_id) ON DELETE RESTRICT;

CREATE TABLE table_read_artifact (
  artifact_id       text PRIMARY KEY,
  table_id          text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  artifact_version  integer NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  superseded_by     text REFERENCES table_read_artifact (artifact_id) ON DELETE SET NULL,
  superseded_at     timestamptz,
  cells             jsonb,
  merges            jsonb,
  parse_warnings    jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (table_id, artifact_version)
);

COMMENT ON TABLE table_read_artifact IS '006 TableReadArtifact。大容量 cells は jsonb またはオブジェクトストレージキーへ逃がし可（015 §7.4）。';
COMMENT ON COLUMN table_read_artifact.is_latest IS '非正規化キャッシュ。真実は superseded 鎖（015 §10）。';

CREATE TABLE judgment_result (
  judgment_id       text PRIMARY KEY,
  table_id          text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  decision          text NOT NULL,
  taxonomy_code     text,
  artifact_version  integer NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  superseded_by     text REFERENCES judgment_result (judgment_id) ON DELETE SET NULL,
  superseded_at     timestamptz,
  evidence          jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (table_id, artifact_version)
);
-- decision: 002 の列挙。decision_recommendation は confidence_evaluation のみ（015 §7.5）。

COMMENT ON TABLE judgment_result IS '002 Judgment。011 decision_recommendation は保持しない（015 §7.5）。';

CREATE TABLE normalized_dataset (
  dataset_id        text PRIMARY KEY,
  table_id          text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  normalization_status text NOT NULL,
  artifact_version  integer NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  superseded_by     text REFERENCES normalized_dataset (dataset_id) ON DELETE SET NULL,
  superseded_at     timestamptz,
  rows              jsonb,
  trace_map         jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (table_id, artifact_version),
  CONSTRAINT normalized_dataset_status_chk CHECK (normalization_status IN (
    'PENDING', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED'
  ))
);
-- TODO: normalization_status の完全列挙は SPEC-TI-003/006 と突合。

COMMENT ON TABLE normalized_dataset IS '003 の主成果物。metadata_id とは別行・別 PK（015 §7.6）。';

CREATE TABLE analysis_metadata (
  metadata_id       text PRIMARY KEY,
  dataset_id        text NOT NULL REFERENCES normalized_dataset (dataset_id) ON DELETE RESTRICT,
  table_id          text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  grain             text,
  artifact_version  integer NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  superseded_by     text REFERENCES analysis_metadata (metadata_id) ON DELETE SET NULL,
  superseded_at     timestamptz,
  dimensions        jsonb,
  measures          jsonb,
  review_points     jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (dataset_id)
);

COMMENT ON TABLE analysis_metadata IS '004 の主成果物。review_points は 006 準拠で jsonb（015 §7.7）。';

CREATE TABLE confidence_evaluation (
  evaluation_id           text PRIMARY KEY,
  table_id                text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  metadata_id             text NOT NULL REFERENCES analysis_metadata (metadata_id) ON DELETE RESTRICT,
  dataset_id              text REFERENCES normalized_dataset (dataset_id) ON DELETE SET NULL,
  decision_recommendation text NOT NULL,
  artifact_version        integer NOT NULL,
  is_latest               boolean NOT NULL DEFAULT true,
  superseded_by           text REFERENCES confidence_evaluation (evaluation_id) ON DELETE SET NULL,
  superseded_at           timestamptz,
  scores                  jsonb,
  explanation             jsonb,
  feature_snapshot_hash   text,
  created_at              timestamptz NOT NULL DEFAULT now()
);
-- 002 の decision は格納しない（015 §7.10）。decision_recommendation: 011。

COMMENT ON TABLE confidence_evaluation IS '011。evaluation_id = API evaluation_ref（015 §5.2, §7.10）。';

CREATE TABLE human_review_session (
  session_id        text PRIMARY KEY,
  workspace_id      text NOT NULL,
  table_id          text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  metadata_id       text NOT NULL REFERENCES analysis_metadata (metadata_id) ON DELETE RESTRICT,
  state             text NOT NULL,
  pending_questions jsonb,
  pending_job_id    text REFERENCES analysis_job (job_id) ON DELETE SET NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT human_review_session_state_chk CHECK (state IN (
    'OPEN', 'IN_PROGRESS', 'WAITING_RERUN', 'CLOSED_RESOLVED', 'CLOSED_UNRESOLVED'
  ))
);
-- TODO: state 列挙の完全版は SPEC-TI-005/006 §6 と突合。禁止遷移は主にアプリ層（015 §9）。

COMMENT ON TABLE human_review_session IS '005。suppression の詳細は suppression_record へ（015 §7.8, 付録 A）。';

CREATE TABLE human_review_answer (
  answer_id       text PRIMARY KEY,
  session_id      text NOT NULL REFERENCES human_review_session (session_id) ON DELETE CASCADE,
  point_id        text NOT NULL,
  answer_type     text,
  selected_option text,
  free_text       text,
  region_ref      jsonb,
  client_nonce    text,
  answered_by     text,
  answered_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, client_nonce)
);
-- TODO: client_nonce 一意は 014 次版と整合。運用で無い場合は NULL 許容＋部分一意の見直し。

COMMENT ON TABLE human_review_answer IS '006 answers[] の 1 行 1 回答（015 §7.9）。';

CREATE TABLE suggestion_set (
  suggestion_run_id   text PRIMARY KEY,
  workspace_id        text NOT NULL,
  table_id            text NOT NULL REFERENCES table_scope (table_id) ON DELETE RESTRICT,
  metadata_id         text NOT NULL REFERENCES analysis_metadata (metadata_id) ON DELETE RESTRICT,
  dataset_id          text REFERENCES normalized_dataset (dataset_id) ON DELETE SET NULL,
  evaluation_id       text REFERENCES confidence_evaluation (evaluation_id) ON DELETE SET NULL,
  session_id          text REFERENCES human_review_session (session_id) ON DELETE SET NULL,
  job_id              text REFERENCES analysis_job (job_id) ON DELETE SET NULL,
  suppression_applied jsonb,
  analysis_candidates jsonb,
  created_at          timestamptz NOT NULL DEFAULT now()
);
-- 方針 A: 別テーブル suggestion_run は置かない（015 §7.11）。
-- TODO: suggestion_candidate サテライトは初版省略。候補は analysis_candidates jsonb に集約可（015 §7.12）。

COMMENT ON TABLE suggestion_set IS '013。主入力 metadata_id 必須。suggestion_run_id = API suggestion_run_ref（015 §5.2, §7.11）。';
COMMENT ON COLUMN suggestion_set.suppression_applied IS '005 を読んだ結果の投影; 正本は suppression_record + 005（015 付録 A）。';

CREATE TABLE job_stage_run (
  job_stage_run_id    text PRIMARY KEY,
  job_id              text NOT NULL REFERENCES analysis_job (job_id) ON DELETE CASCADE,
  stage               text NOT NULL,
  status              text NOT NULL,
  artifact_version    integer,
  output_dataset_id   text REFERENCES normalized_dataset (dataset_id) ON DELETE SET NULL,
  output_metadata_id  text REFERENCES analysis_metadata (metadata_id) ON DELETE SET NULL,
  started_at          timestamptz,
  ended_at            timestamptz,
  stage_detail        jsonb,
  CONSTRAINT job_stage_run_stage_chk CHECK (stage IN (
    'READ', 'JUDGE', 'NORMALIZE', 'META', 'REVIEW', 'SUGGESTION', 'EVALUATION'
  )),
  CONSTRAINT job_stage_run_status_chk CHECK (status IN (
    'PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'SKIPPED'
  ))
);
-- TODO: (job_id, stage, artifact_version) の一意制約は再試行ポリシー確定後（015 §7.2）。
-- TODO: evaluation_run 専用テーブルは置かない。必要なら別マイグレーションで分離。

COMMENT ON TABLE job_stage_run IS '001〜004 等の段階別実行行（015 §7.2）。';

-- =============================================================================
-- 3. relation / control tables
-- =============================================================================

CREATE TABLE suppression_record (
  suppression_id   text PRIMARY KEY,
  session_id       text NOT NULL REFERENCES human_review_session (session_id) ON DELETE CASCADE,
  point_id         text,
  candidate_id     text,
  suppression_kind text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  created_by       text,
  context          jsonb
);

COMMENT ON TABLE suppression_record IS '005 suppression の DB 保持推奨形（015 §7.13, 付録 A）。';

CREATE TABLE artifact_relation (
  relation_id       text PRIMARY KEY,
  from_artifact_type text NOT NULL,
  from_id           text NOT NULL,
  to_artifact_type  text NOT NULL,
  to_id             text NOT NULL,
  relation_kind     text NOT NULL,
  job_id            text REFERENCES analysis_job (job_id) ON DELETE SET NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT artifact_relation_kind_chk CHECK (relation_kind IN (
    'SUPERSEDES', 'DERIVED_FROM', 'TRIGGERED_BY_JOB'
  ))
);
-- TODO: from_id/to_id は多型参照のため FK は張らない。整合はアプリ＋監査（015 §7.14）。

COMMENT ON TABLE artifact_relation IS 'lineage / rerun。旧 metadata_id → 新 metadata_id 等（015 §7.14, §10）。';

CREATE TABLE audit_log (
  audit_id       text PRIMARY KEY,
  workspace_id   text NOT NULL,
  actor_id       text,
  action         text NOT NULL,
  resource_type  text,
  resource_id    text,
  job_id         text REFERENCES analysis_job (job_id) ON DELETE SET NULL,
  session_id     text REFERENCES human_review_session (session_id) ON DELETE SET NULL,
  request_id     text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  payload_diff   jsonb
);

COMMENT ON TABLE audit_log IS 'API / ジョブ / 人確認の追跡（015 §7.15）。';

-- =============================================================================
-- 4. indexes
-- =============================================================================

CREATE INDEX idx_analysis_job_workspace_status_created
  ON analysis_job (workspace_id, status, created_at);

CREATE INDEX idx_analysis_job_table_id ON analysis_job (table_id);

CREATE INDEX idx_table_read_artifact_table_id ON table_read_artifact (table_id);
CREATE INDEX idx_table_read_artifact_table_latest ON table_read_artifact (table_id, is_latest);

CREATE INDEX idx_judgment_result_table_id ON judgment_result (table_id);
CREATE INDEX idx_judgment_result_table_latest ON judgment_result (table_id, is_latest);

CREATE INDEX idx_normalized_dataset_table_id ON normalized_dataset (table_id);
CREATE INDEX idx_normalized_dataset_table_latest ON normalized_dataset (table_id, is_latest);

CREATE INDEX idx_analysis_metadata_table_id ON analysis_metadata (table_id);
CREATE INDEX idx_analysis_metadata_dataset_id ON analysis_metadata (dataset_id);

CREATE INDEX idx_confidence_eval_metadata_id ON confidence_evaluation (metadata_id);
CREATE INDEX idx_confidence_eval_table_id ON confidence_evaluation (table_id);
CREATE INDEX idx_confidence_eval_dataset_id ON confidence_evaluation (dataset_id);

CREATE INDEX idx_human_review_session_metadata_id ON human_review_session (metadata_id);
CREATE INDEX idx_human_review_session_table_id ON human_review_session (table_id);

CREATE INDEX idx_human_review_answer_session_id ON human_review_answer (session_id);

CREATE INDEX idx_suggestion_set_metadata_id ON suggestion_set (metadata_id);
CREATE INDEX idx_suggestion_set_table_id ON suggestion_set (table_id);
CREATE INDEX idx_suggestion_set_dataset_id ON suggestion_set (dataset_id);
CREATE INDEX idx_suggestion_set_evaluation_id ON suggestion_set (evaluation_id);
CREATE INDEX idx_suggestion_set_session_id ON suggestion_set (session_id);

CREATE INDEX idx_job_stage_run_job_id ON job_stage_run (job_id);
CREATE INDEX idx_job_stage_run_output_dataset ON job_stage_run (output_dataset_id);
CREATE INDEX idx_job_stage_run_output_metadata ON job_stage_run (output_metadata_id);

CREATE INDEX idx_suppression_record_session_id ON suppression_record (session_id);

CREATE INDEX idx_artifact_relation_job_id ON artifact_relation (job_id);
CREATE INDEX idx_artifact_relation_from ON artifact_relation (from_artifact_type, from_id);
CREATE INDEX idx_artifact_relation_to ON artifact_relation (to_artifact_type, to_id);

CREATE INDEX idx_audit_log_created_at ON audit_log (created_at);
CREATE INDEX idx_audit_log_workspace_created ON audit_log (workspace_id, created_at);

-- TODO: latest 解決の部分索引 (WHERE is_latest = true) は負荷見て追加（015 §12）。

-- =============================================================================
-- 5. TODO
-- =============================================================================
-- TODO: evaluation_run テーブルを別立てするかは負荷・観測要件で判断（015 §5.1）。
-- TODO: suggestion_candidate サテライト化は検索要件が出たら（015 §7.12）。
-- TODO: (workspace_id, idempotency_key) の部分一意は運用ポリシー確定後（015 §7.1）。
-- TODO: human_review_answer の同一 point_id 上書きポリシーは 005 に従い DB 制約またはビューで表現。
-- TODO: RLS（workspace_id）とロールは 014/015 §13 と合わせてマイグレーションで実装。
-- TODO: OpenAPI × 006 × 本 DDL の列レベル対応表を別紙で整備。
