from django.conf import settings
from django.db import models

from workspaces.models import Workspace


class DatasetStatus(models.TextChoices):
    UPLOADED = "uploaded", "uploaded"
    PROFILING = "profiling", "profiling"
    PROFILED = "profiled", "profiled"
    MAPPING_READY = "mapping_ready", "mapping_ready"
    PREVIEWED = "previewed", "previewed"
    ERROR = "error", "error"


class FileType(models.TextChoices):
    CSV = "csv", "csv"
    XLSX = "xlsx", "xlsx"
    UNKNOWN = "unknown", "unknown"


class InferredType(models.TextChoices):
    STRING = "string", "string"
    NUMBER = "number", "number"
    DATE = "date", "date"
    UNKNOWN = "unknown", "unknown"


class SemanticLabel(models.TextChoices):
    COMPANY_NAME = "company_name", "company_name"
    PERSON_NAME = "person_name", "person_name"
    PRODUCT_NAME = "product_name", "product_name"
    QUANTITY = "quantity", "quantity"
    DATE = "date", "date"
    DATETIME = "datetime", "datetime"
    EMAIL = "email", "email"
    PHONE = "phone", "phone"
    PREFECTURE = "prefecture", "prefecture"
    CITY = "city", "city"
    AMOUNT = "amount", "amount"
    AMOUNT_JPY = "amount_jpy", "amount_jpy"
    UNIT_PRICE = "unit_price", "unit_price"
    CATEGORY = "category", "category"
    MEMO = "memo", "memo"
    COUNT = "count", "count"
    ASSIGNEE = "assignee", "assignee"
    DEPARTMENT = "department", "department"
    CUSTOMER = "customer", "customer"
    PRODUCT = "product", "product"
    STATUS = "status", "status"
    UNKNOWN = "unknown", "unknown"
    IGNORE = "ignore", "ignore"


class SemanticLabelSource(models.TextChoices):
    AI = "ai", "ai"
    USER = "user", "user"


class SheetStructureStatus(models.TextChoices):
    """列・行構造の解釈状態（自動判定の信頼度とユーザー確認）。"""

    AUTO_OK = "auto_ok", "自動判定で問題なし"
    NEEDS_REVIEW = "needs_review", "要確認（ヘッダー行の確認が必要）"
    CONFIRMED = "confirmed", "確認済み"


class Dataset(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="datasets/%Y/%m/%d/")
    file_type = models.CharField(
        max_length=16,
        choices=FileType.choices,
        default=FileType.UNKNOWN,
    )
    status = models.CharField(
        max_length=32,
        choices=DatasetStatus.choices,
        default=DatasetStatus.UPLOADED,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class DatasetFile(models.Model):
    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        related_name="file_record",
    )
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    storage_path = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DatasetSheet(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="sheets",
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    selected = models.BooleanField(default=False)
    row_count = models.PositiveIntegerField(null=True, blank=True)
    column_count = models.PositiveIntegerField(null=True, blank=True)
    preview_ready = models.BooleanField(default=False)
    analysis = models.JSONField(default=dict, blank=True)
    structure_status = models.CharField(
        max_length=32,
        choices=SheetStructureStatus.choices,
        default=SheetStructureStatus.AUTO_OK,
    )
    header_row_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="1始まりの行番号。未設定時は自動検出。CSV/XLSX 共通。",
    )

    class Meta:
        ordering = ["order", "id"]
        unique_together = [["dataset", "name"]]

    def __str__(self) -> str:
        return f"{self.dataset_id}:{self.name}"

    def structure_needs_user_action(self) -> bool:
        return self.structure_status == SheetStructureStatus.NEEDS_REVIEW


class DatasetColumnProfile(models.Model):
    sheet = models.ForeignKey(
        DatasetSheet,
        on_delete=models.CASCADE,
        related_name="column_profiles",
    )
    column_name = models.CharField(max_length=512)
    normalized_name = models.CharField(max_length=512, default="")
    inferred_type = models.CharField(
        max_length=32,
        choices=InferredType.choices,
        default=InferredType.UNKNOWN,
    )
    null_ratio = models.FloatField(default=0.0)
    unique_ratio = models.FloatField(default=0.0)
    sample_values = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    semantic_label = models.CharField(
        max_length=32,
        choices=SemanticLabel.choices,
        default=SemanticLabel.UNKNOWN,
    )
    semantic_label_source = models.CharField(
        max_length=16,
        choices=SemanticLabelSource.choices,
        default=SemanticLabelSource.AI,
    )

    class Meta:
        unique_together = [["sheet", "column_name"]]

    def __str__(self) -> str:
        return f"{self.column_name} ({self.inferred_type})"


class DatasetPreview(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="previews",
    )
    sheet = models.ForeignKey(
        DatasetSheet,
        on_delete=models.CASCADE,
        related_name="previews",
    )
    rows = models.JSONField(default=list)
    columns = models.JSONField(default=list)
    summary = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DatasetProcessingJob(models.Model):
    class JobType(models.TextChoices):
        PREVIEW = "preview", "preview"
        PROFILE = "profile", "profile"
        MAPPING = "mapping", "mapping"

    class JobStatus(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
    )
    sheet = models.ForeignKey(
        DatasetSheet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processing_jobs",
    )
    job_type = models.CharField(max_length=16, choices=JobType.choices)
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
