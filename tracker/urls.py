from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('', views.landing_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='tracker/password_reset.html',
        email_template_name='tracker/password_reset_email.html',
        subject_template_name='tracker/password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='tracker/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='tracker/password_reset_confirm.html',
        success_url='/password-reset/complete/',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='tracker/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Habits
    path('habits/', views.habit_list, name='habit_list'),
    path('habits/create/', views.habit_create, name='habit_create'),
    path('habits/<int:pk>/', views.habit_detail, name='habit_detail'),
    path('habits/<int:pk>/edit/', views.habit_edit, name='habit_edit'),
    path('habits/<int:pk>/delete/', views.habit_delete, name='habit_delete'),
    path('habits/<int:pk>/toggle/', views.toggle_habit, name='toggle_habit'),
    path('habits/<int:pk>/archive/', views.archive_habit, name='archive_habit'),
    path('habits/archived/', views.archived_habits, name='archived_habits'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Streak Freeze
    path('habits/<int:pk>/freeze/', views.use_streak_freeze, name='use_streak_freeze'),

    # Calendar
    path('calendar/', views.calendar_view, name='calendar_view'),

    # Strava Integration
    path('strava/connect/', views.strava_connect, name='strava_connect'),
    path('strava/callback/', views.strava_callback, name='strava_callback'),
    path('strava/sync/', views.strava_sync, name='strava_sync'),
    path('strava/mock/authorize/', views.strava_mock_authorize, name='strava_mock_authorize'),
    path('strava/mock/callback/', views.strava_mock_callback, name='strava_mock_callback'),

    # Spotify Integration
    path('spotify/connect/', views.spotify_connect, name='spotify_connect'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('spotify/sync/', views.spotify_sync, name='spotify_sync'),
    path('spotify/mock/authorize/', views.spotify_mock_authorize, name='spotify_mock_authorize'),
    path('spotify/mock/callback/', views.spotify_mock_callback, name='spotify_mock_callback'),
    path('spotify/player/', views.spotify_player_save, name='spotify_player_save'),
    path('spotify/token/', views.spotify_token, name='spotify_token'),
    path('spotify/search/', views.spotify_search, name='spotify_search'),
    path('spotify/play/', views.spotify_play, name='spotify_play'),
]
