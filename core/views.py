# Standard library
from datetime import timedelta

# Django core
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import (
    Case,
    When,
    Value,
    IntegerField,
    Count,
    OuterRef,
    Subquery,
    Sum,
)
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Avg
from django.utils.timezone import now
# Local app
from .models import Quest, Logger, Category
from .forms import CategoryForm, QuestForm, LoggerForm
from .utils import roll_exploding_d10


@login_required
def home(request):
    total_quests = Quest.objects.count()
    active_quests = Quest.objects.filter(end_date__isnull=True).count()

    today = now().date()
    logs_today = Logger.objects.filter(timestamp__date=today).count()

    context = {
        "total_quests": total_quests,
        "active_quests": active_quests,
        "logs_today": logs_today,
    }
    return render(request, "core/home.html", context)

@login_required
def quest_list(request):
    # Active first (end_date is NULL), then most recently updated
    quests = (
        Quest.objects.select_related("category")
        .annotate(
            is_ended=Case(
                When(end_date__isnull=True, then=Value(0)),  # active
                default=Value(1),  # ended
                output_field=IntegerField(),
            )
        )
        .order_by("is_ended", "-updated_at")
    )

    return render(request, "core/quest_list.html", {"quests": quests})

@login_required
def quest_detail(request, pk):
    quest = get_object_or_404(
        Quest.objects.select_related("category"),
        pk=pk,
    )

    # --- Rollups (all time) ---
    rollups = quest.logs.aggregate(
        total_sessions=Count("id"),
        total_completed=Count("id", filter=Q(completed=True)),
        total_payout=Sum("payout"),
        last_activity=Max("timestamp"),
    )

    total_sessions = rollups["total_sessions"] or 0
    total_completed = rollups["total_completed"] or 0
    total_payout = rollups["total_payout"] or 0
    last_activity = rollups["last_activity"]  # can be None

    # --- History range selector ---
    range_key = request.GET.get("range", "recent")  # recent | week | all

    logs_qs = quest.logs.order_by("-timestamp")

    if range_key == "week":
        start = timezone.now() - timedelta(days=7)
        logs_qs = logs_qs.filter(timestamp__gte=start)
        logs = logs_qs[:100]
    elif range_key == "all":
        logs = logs_qs[:300]  # cap for MVP
    else:
        range_key = "recent"
        logs = logs_qs[:20]

    context = {
        "quest": quest,
        "total_sessions": total_sessions,
        "total_completed": total_completed,
        "total_payout": total_payout,
        "last_activity": last_activity,
        "range": range_key,
        "logs": logs,
    }
    return render(request, "core/quest_detail.html", context)


@login_required
def log_list(request):
    completed = request.GET.get("completed", "all")  # all | yes | no
    date_range = request.GET.get("range", "")        # "" | today | 7d
    category_id = request.GET.get("category", "")    # uuid or ""

    qs = (
        Logger.objects
        .select_related("quest", "quest__category")
        .order_by("-timestamp")
    )

    # Completed filter
    if completed == "yes":
        qs = qs.filter(completed=True)
    elif completed == "no":
        qs = qs.filter(completed=False)

    # Date range quick filters
    if date_range == "today":
        start = now().date()
        qs = qs.filter(timestamp__date=start)
    elif date_range == "7d":
        start_dt = now() - timedelta(days=7)
        qs = qs.filter(timestamp__gte=start_dt)

    # Category filter
    if category_id:
        qs = qs.filter(quest__category_id=category_id)

    # Pagination (recommended)
    paginator = Paginator(qs, 25)  # 25 logs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.order_by("name")

    context = {
        "page_obj": page_obj,
        "completed": completed,
        "date_range": date_range,
        "category_id": category_id,
        "categories": categories,
    }
    return render(request, "core/log_list.html", context)

@login_required
def category_list(request):
    categories = (
        Category.objects
        .annotate(quest_count=Count("quests"))
        .order_by("name")
    )
    return render(request, "core/category_list.html", {"categories": categories})

@login_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)

    quests = (
        Quest.objects.select_related("category")
        .filter(category=category)
        .annotate(
            is_ended=Case(
                When(end_date__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("is_ended", "-updated_at")
    )

    return render(
        request,
        "core/category_detail.html",
        {"category": category, "quests": quests},
    )

@login_required
def category_list(request):
    categories = (
        Category.objects
        .annotate(quest_count=Count("quests"))
        .order_by("name")
    )
    return render(request, "core/category_list.html", {"categories": categories})


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Created category: {cat.name}")
            return redirect("category_list")
    else:
        form = CategoryForm()

    return render(request, "core/category_form.html", {"form": form, "mode": "create"})


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Updated category: {cat.name}")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "core/category_form.html",
        {"form": form, "mode": "edit", "category": category},
    )


@login_required
def category_delete(request, pk):
    category = get_object_or_404(
        Category.objects.annotate(quest_count=Count("quests")),
        pk=pk
    )

    if category.quest_count > 0:
        messages.error(request, "Can't delete a category that still has quests. Reassign those quests first.")
        return redirect("category_list")

    if request.method == "POST":
        name = category.name
        category.delete()
        messages.success(request, f"Deleted category: {name}")
        return redirect("category_list")

    # tiny confirmation page (optional)
    return render(request, "core/category_confirm_delete.html", {"category": category})

@login_required
def quest_create(request):
    if request.method == "POST":
        form = QuestForm(request.POST)
        if form.is_valid():
            quest = form.save()
            return redirect("quest_detail", pk=quest.id)  # ✅ redirect to story page
    else:
        form = QuestForm()

    return render(request, "core/quest_form.html", {"form": form, "mode": "create"})

@login_required
def quest_edit(request, pk):
    quest = get_object_or_404(Quest, pk=pk)

    is_ended = quest.end_date is not None
    allow_notes_only = is_ended  # lock history if ended

    if request.method == "POST":
        form = QuestForm(request.POST, instance=quest, allow_notes_only=allow_notes_only)
        if form.is_valid():
            updated = form.save(commit=False)

            # Server-side safety: if ended, only allow notes to change
            if is_ended:
                updated.title = quest.title
                updated.category = quest.category
                updated.start_date = quest.start_date
                updated.end_date = quest.end_date
                updated.limited_mobility = quest.limited_mobility

            updated.save()
            messages.success(request, "Quest updated.")
            return redirect("quest_detail", pk=quest.id)
    else:
        form = QuestForm(instance=quest, allow_notes_only=allow_notes_only)

    lock_reason = None
    if is_ended:
        lock_reason = "This quest has ended, so history fields are locked. You can still edit notes."

    return render(
        request,
        "core/quest_form.html",
        {
            "form": form,
            "mode": "edit",
            "quest": quest,
            "is_ended": is_ended,
            "lock_reason": lock_reason,
        },
    )

@login_required
def _active_quest_queryset(mode: str):
    last_ts = Logger.objects.filter(quest=OuterRef("pk")).order_by("-timestamp").values("timestamp")[:1]
    last_payout = Logger.objects.filter(quest=OuterRef("pk")).order_by("-timestamp").values("payout")[:1]

    qs = (
        Quest.objects.active()
        .select_related("category")
        .annotate(last_logged=Subquery(last_ts), last_payout=Subquery(last_payout))
    )

    if mode == "limited":
        qs = qs.by_mobility(True)

    return qs

@login_required
def active_quests_page(request):
    mode = request.GET.get("mode", "normal").lower()
    qs = _active_quest_queryset(mode)
    total_count = qs.count()
    quests = qs.order_by("-updated_at")[:3]
    return render(request, "core/active_quests.html", {"mode": mode, "quests": quests, "total_count": total_count})

@login_required
def active_quests_partial(request):
    mode = request.GET.get("mode", "normal").lower()
    qs = _active_quest_queryset(mode)
    total_count = qs.count()
    quests = qs.order_by("-updated_at")[:3]
    return render(request, "core/partials/_active_quest_cards.html", {"mode": mode, "quests": quests, "total_count": total_count})

@login_required
def logger_start(request, quest_id):
    quest = get_object_or_404(Quest, pk=quest_id)

    if quest.end_date is not None:
        messages.error(request, "This quest has ended, so you can’t start a new log for it.")
        return redirect("quest_detail", pk=quest.id)

    log = Logger.objects.create(quest=quest)
    return redirect("logger_detail", pk=log.id)


@login_required
def logger_detail(request, pk):
    log = get_object_or_404(
        Logger.objects.select_related("quest", "quest__category"),
        pk=pk
    )

    if request.method == "POST":
        form = LoggerForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved")

            # Decide where to go based on which button was clicked
            if "save_back_today" in request.POST:
                return redirect("today")

            if "start_another" in request.POST:
                return redirect("today")

            return redirect("logger_detail", pk=log.id)  # PRG: stay
    else:
        form = LoggerForm(instance=log)

    return render(request, "core/logger_detail.html", {"log": log, "form": form})

@login_required
def logger_start_htmx(request, quest_id):
    quest = get_object_or_404(Quest.objects.select_related("category"), pk=quest_id)

    if quest.end_date is not None:
        return render(
            request,
            "core/partials/_active_quest_start_error_card.html",
            {"quest": quest, "error": "Quest is ended — can’t start a new log."},
            status=400,
        )

    log = Logger.objects.create(quest=quest)
    return render(
        request,
        "core/partials/_active_quest_started_card.html",
        {"quest": quest, "log": log},
    )

@login_required
def active_quests_page(request):
    mode = request.GET.get("mode", "normal").lower()

    qs = Quest.objects.active().select_related("category")
    if mode == "limited":
        qs = qs.by_mobility(True)

    total_count = qs.count()
    quests = qs.order_by("-updated_at")[:3]

    return render(request, "core/active_quests.html", {
        "mode": mode,
        "quests": quests,
        "total_count": total_count,
    })


@login_required
def active_quests_partial(request):
    mode = request.GET.get("mode", "normal").lower()

    qs = Quest.objects.active().select_related("category")
    if mode == "limited":
        qs = qs.by_mobility(True)

    total_count = qs.count()
    quests = qs.order_by("-updated_at")[:3]

    return render(request, "core/partials/_active_quest_cards.html", {
        "quests": quests,
        "total_count": total_count,
        "mode": mode,
    })

@login_required
@require_POST
def logger_finish(request, pk):
    log = get_object_or_404(Logger, pk=pk)
    if not log.completed:
        log.completed = True
        log.save(update_fields=["completed"])
    messages.success(request, "Saved")
    return redirect("logger_detail", pk=log.id)


@login_required
@require_POST
def logger_toggle_completed(request, pk):
    log = get_object_or_404(Logger, pk=pk)
    log.completed = not log.completed
    log.save(update_fields=["completed"])
    return render(request, "core/partials/_logger_status_row.html", {"log": log})

@login_required
@require_POST
def logger_update_payout(request, pk):
    log = get_object_or_404(Logger, pk=pk)

    raw = request.POST.get("payout", "").strip()
    if raw == "":
        log.payout = None
        log.save(update_fields=["payout"])
        return render(request, "core/partials/_logger_payout_field.html", {"log": log})

    try:
        log.payout = int(raw)
    except ValueError:
        # Re-render with a simple inline error message
        return render(request, "core/partials/_logger_payout_field_error.html", {"log": log, "error": "Payout must be an integer."}, status=400)

    log.save(update_fields=["payout"])
    return render(request, "core/partials/_logger_payout_field.html", {"log": log})

@login_required
@require_POST
def logger_roll_payout(request, pk):
    log = get_object_or_404(
        Logger.objects.select_related("quest", "quest__category"),
        pk=pk
    )

    # Guardrail: don't overwrite existing payout unless confirmed
    if log.payout is not None and request.POST.get("confirm") != "1":
        form = LoggerForm(instance=log)
        return render(
            request,
            "core/partials/_logger_payout_block.html",
            {
                "log": log,
                "form": form,
                "needs_confirm": True,
                "confirm_message": "Replace existing payout with a roll?",
            },
            status=409,
        )

    result = roll_exploding_d10()
    total = int(result["total"])
    rolls = result["rolls"]

    log.payout = total

    # Optional: append roll line to notes (safe, non-destructive)
    roll_line = f"Roll: {'+'.join(str(r) for r in rolls)} = {total}"
    if log.notes:
        log.notes = log.notes.rstrip() + "\n" + roll_line
    else:
        log.notes = roll_line

    log.save(update_fields=["payout", "notes"])

    form = LoggerForm(instance=log)
    return render(
        request,
        "core/partials/_logger_payout_block.html",
        {
            "log": log,
            "form": form,
            "needs_confirm": False,
            "rolls": rolls,
            "total": total,
        },
    )

@login_required
def today_page(request):
    # Mode: same semantics you decided earlier.
    # If your current rule is:
    #   mode=limited => only limited_mobility=True
    #   mode=normal  => include BOTH limited and non-limited
    # then normal means "no filter".
    mode = request.GET.get("mode", "normal").lower()
    limited_only = (mode == "limited")

    # Active quests
    qs = Quest.objects.active().select_related("category")

    if limited_only:
        qs = qs.filter(limited_mobility=True)
    # else: normal = include both, no filter

    quests = list(qs.order_by("-updated_at")[:3])  # or order_by("?") for random-ish

    # Today window: [today_start, tomorrow_start)
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    today_logs_qs = (
        Logger.objects
        .select_related("quest", "quest__category")
        .filter(timestamp__gte=today_start, timestamp__lt=tomorrow_start)
        .order_by("-timestamp")
    )

    # Totals
    totals = today_logs_qs.aggregate(
        sessions_started=Count("id"),
        completed_sessions=Count("id", filter=Logger.objects.filter(completed=True).query.where),  # see note below
        total_payout=Sum("payout"),
    )

    # Django 6 note: easiest / clearest is to compute completed separately:
    sessions_started = totals["sessions_started"] or 0
    total_payout = totals["total_payout"] or 0

    completed_sessions = today_logs_qs.filter(completed=True).count()

    context = {
        "mode": mode,
        "quests": quests,
        "today_logs": today_logs_qs[:50],  # cap for UI
        "sessions_started": sessions_started,
        "completed_sessions": completed_sessions,
        "total_payout": total_payout,
        "today_start": today_start,
    }
    return render(request, "core/today.html", context)

@login_required
def stats_page(request):
    now = timezone.now()
    start = now - timedelta(days=7)

    logs = (
        Logger.objects
        .select_related("quest", "quest__category")
        .filter(timestamp__gte=start, timestamp__lte=now)
    )

    # Overall stats (last 7 days)
    overall = logs.aggregate(
        total_sessions=Count("id"),
        completed_sessions=Count("id", filter=Q(completed=True)),
        total_payout=Sum("payout"),
        avg_payout=Avg("payout"),
    )

    total_sessions = overall["total_sessions"] or 0
    completed_sessions = overall["completed_sessions"] or 0
    total_payout = overall["total_payout"] or 0
    avg_payout = overall["avg_payout"] or 0

    completion_rate = (completed_sessions / total_sessions) if total_sessions else 0

    # Top 5 quests by payout (last 7 days)
    top_quests_by_payout = (
        logs.values("quest__id", "quest__title", "quest__category__name")
        .annotate(
            payout=Sum("payout"),
            sessions=Count("id"),
            completed=Count("id", filter=Q(completed=True)),
        )
        .order_by("-payout", "-sessions")[:5]
    )

    # Top 5 quests by session count (last 7 days)
    top_quests_by_sessions = (
        logs.values("quest__id", "quest__title", "quest__category__name")
        .annotate(
            sessions=Count("id"),
            payout=Sum("payout"),
            completed=Count("id", filter=Q(completed=True)),
        )
        .order_by("-sessions", "-payout")[:5]
    )

    # Optional: by category (last 7 days)
    by_category = (
        logs.values("quest__category__id", "quest__category__name")
        .annotate(
            sessions=Count("id"),
            completed=Count("id", filter=Q(completed=True)),
            payout=Sum("payout"),
        )
        .order_by("-payout", "-sessions")
    )

    context = {
        "start": start,
        "end": now,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_payout": total_payout,
        "avg_payout": avg_payout,
        "completion_rate": completion_rate,
        "top_quests_by_payout": top_quests_by_payout,
        "top_quests_by_sessions": top_quests_by_sessions,
        "by_category": by_category,
    }
    return render(request, "core/stats.html", context)

@login_required
def quest_delete_confirm(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    return render(request, "core/quest_confirm_delete.html", {"quest": quest})

@login_required
@require_POST
def quest_delete(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    quest.delete()
    return redirect("quest_list")

@login_required
def logger_delete_confirm(request, pk):
    log = get_object_or_404(Logger, pk=pk)
    return render(request, "core/logger_confirm_delete.html", {"log": log})

@login_required
@require_POST
def logger_delete(request, pk):
    log = get_object_or_404(Logger, pk=pk)
    log.delete()
    return redirect("log_list")

@login_required
@require_POST
def quest_delete(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    quest.delete()
    return redirect("quest_list")


@login_required
def logger_edit(request, pk):
    log = get_object_or_404(Logger, pk=pk)

    if request.method == "POST":
        form = LoggerForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            return redirect("logger_detail", pk=log.pk)
    else:
        form = LoggerForm(instance=log)

    return render(request, "core/logger_edit.html", {"log": log, "form": form})


@login_required
@require_POST
def logger_delete(request, pk):
    log = get_object_or_404(Logger, pk=pk)
    quest_id = log.quest_id  # your FK is named quest, so this works
    log.delete()
    return redirect("quest_detail", pk=quest_id)
