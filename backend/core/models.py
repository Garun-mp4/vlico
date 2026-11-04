import uuid
from pathlib import PurePosixPath
from django.core.validators import MinValueValidator
from django.db import models
from .storage import PrivateMediaStorage


def media_path(instance, filename):
    return f"projects/{instance.project_id}/{uuid.uuid4().hex}{PurePosixPath(filename).suffix.lower()}"


def attachment_path(instance, filename):
    return f"leads/{instance.lead_id}/{uuid.uuid4().hex}{PurePosixPath(filename).suffix.lower()}"


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Service(Timestamped):
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Project(Timestamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликован"
        ARCHIVED = "archived", "Архив"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    object_type = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=200, blank=True)
    editor_notes = models.TextField(blank=True)
    task = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    materials = models.TextField(blank=True)
    area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    services = models.ManyToManyField(Service, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("project", args=[self.slug])

    @property
    def cover_media(self):
        return next((m for m in self.media.all() if m.is_cover), None)

    def __str__(self):
        return self.title


class ProjectMedia(Timestamped):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to=media_path)
    thumbnail = models.ImageField(upload_to=media_path, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    alt = models.CharField(max_length=250, blank=True)
    caption = models.CharField(max_length=250, blank=True)
    section = models.CharField(max_length=12, choices=[("result", "Результат"), ("process", "Монтаж")], default="result")
    is_cover = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["project"], condition=models.Q(is_cover=True), name="one_cover_per_project")]


class PricingVersion(Timestamped):
    title = models.CharField(max_length=120)
    # No fabricated rates are seeded in milestone 1. Calculator follows in milestone 3.
    rates = models.JSONField(default=dict)
    active = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["active"], condition=models.Q(active=True), name="one_active_price_version")]


class Lead(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=20, choices=[(x, x) for x in ("consultation", "measurement", "project", "calculator", "partner")])
    name = models.CharField(max_length=160)
    contact = models.CharField(max_length=250)
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    comment = models.TextField(blank=True)
    source_page = models.CharField(max_length=500, blank=True)
    attribution = models.JSONField(default=dict)
    calculation = models.JSONField(default=dict)
    pricing_version = models.ForeignKey(PricingVersion, null=True, blank=True, on_delete=models.PROTECT)
    consent_at = models.DateTimeField(null=True, blank=True)


class LeadAttachment(Timestamped):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_path, storage=PrivateMediaStorage())
    original_name = models.CharField(max_length=255)


class Delivery(Timestamped):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=20, default="telegram")
    status = models.CharField(max_length=12, choices=[(x, x) for x in ("pending", "sending", "sent", "failed")], default="pending")
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["lead", "channel"], name="one_delivery_per_channel")]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]


class LoginBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
