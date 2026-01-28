from django.urls import path, include
from . import views
from django.contrib import admin


urlpatterns = [
    path("", views.home, name="home"),
   
        # Quests
    path("quests/", views.quest_list, name="quest_list"),
    path("quests/new/", views.quest_create, name="quest_create"),
    path("quests/<uuid:pk>/", views.quest_detail, name="quest_detail"),
    path("quests/<uuid:pk>/edit/", views.quest_edit, name="quest_edit"),
    path("active/", views.active_quests_page, name="active_quests"),
    path("active/partial/", views.active_quests_partial, name="active_quests_partial"),


   
   #Logger 
    path("logs/", views.log_list, name="log_list"),
    path("logger/start/<uuid:quest_id>/", views.logger_start, name="logger_start"),
    path("logger/<uuid:pk>/", views.logger_detail, name="logger_detail"),
    path("logger/start-htmx/<uuid:quest_id>/", views.logger_start_htmx, name="logger_start_htmx"),
    path("logger/<uuid:pk>/finish/", views.logger_finish, name="logger_finish"),
    path("logger/<uuid:pk>/toggle-completed/", views.logger_toggle_completed, name="logger_toggle_completed"),
    path("logger/<uuid:pk>/update-payout/", views.logger_update_payout, name="logger_update_payout"),
    path("logger/<uuid:pk>/roll_payout/", views.logger_roll_payout, name="logger_roll_payout"),



    
    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/<uuid:pk>/", views.category_detail, name="category_detail"),

    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<uuid:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<uuid:pk>/delete/", views.category_delete, name="category_delete"),
    
    #today Stats etc
    path("today/", views.today_page, name="today"),
    path("stats/", views.stats_page, name="stats"),
    # Django auth (login / logout)
    path("accounts/", include("django.contrib.auth.urls")),



]

