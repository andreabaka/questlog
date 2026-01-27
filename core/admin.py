from django.contrib import admin
from .models import Category, Quest, Logger


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "updated_at")
    search_fields = ("name", "notes")
    ordering = ("name",)


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "limited_mobility", "start_date", "end_date", "updated_at")
    list_filter = ("limited_mobility", "category", "end_date")
    search_fields = ("title", "notes")
    ordering = ("-updated_at",)


@admin.register(Logger)
class LoggerAdmin(admin.ModelAdmin):
    list_display = ("quest", "timestamp", "completed", "payout")
    list_filter = ("completed", "quest")
    search_fields = ("quest__title", "notes")
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"
