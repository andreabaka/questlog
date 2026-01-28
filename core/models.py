import uuid
from django.db import models
from django.utils.timezone import now


class QuestQuerySet(models.QuerySet):
    def active(self):
        return self.filter(end_date__isnull=True)

    def ended(self):
        return self.filter(end_date__isnull=False)

    def by_mobility(self, limited: bool):
        return self.filter(limited_mobility=limited)


class QuestManager(models.Manager):
    def get_queryset(self):
        return QuestQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def ended(self):
        return self.get_queryset().ended()

    def by_mobility(self, limited: bool):
        return self.get_queryset().by_mobility(limited)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Quest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quests",
    )


    start_date = models.DateField(null=True, blank=True, default=now)
    end_date = models.DateField(null=True, blank=True)
    limited_mobility = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = QuestManager()


    class Meta:
        indexes = [
            models.Index(fields=["end_date"]),
            models.Index(fields=["limited_mobility", "end_date"]),
        ]
        ordering = ("-updated_at",)
    @property
    def latest_log(self):
        return self.logs.order_by("-timestamp").first()

    @property
    def is_active(self) -> bool:
        return self.end_date is None


    def __str__(self) -> str:
        return self.title


class Logger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="logs")

    timestamp = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    payout = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def is_completed(self) -> bool:
        return bool(self.completed)

    class Meta:
        indexes = [models.Index(fields=["quest", "timestamp"])]
        ordering = ("-timestamp",)

    def __str__(self) -> str:
        return f"{self.quest.title} @ {self.timestamp:%Y-%m-%d %H:%M}"


