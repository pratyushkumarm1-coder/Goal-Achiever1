from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Q
from datetime import timedelta, date
from calendar import monthrange
import json
import re
import time
import requests
import urllib.parse
from django.conf import settings

from .models import Habit, HabitLog, Category, UserProfile, Badge, UserBadge
from .forms import (CustomUserCreationForm, CustomLoginForm, HabitForm,
                    CategoryForm, UserProfileForm, HabitLogNoteForm)


# ─── Landing Page ──────────────────────────────────────────────────────────

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'tracker/landing.html')


# ─── Auth Views ─────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            # Seed default categories
            defaults = [
                ('Health', '#00b894', 'bi-heart-pulse'),
                ('Fitness', '#e17055', 'bi-lightning'),
                ('Learning', '#6c5ce7', 'bi-book'),
                ('Mindfulness', '#fd79a8', 'bi-emoji-smile'),
            ]
            for name, color, icon in defaults:
                Category.objects.create(user=user, name=name, color=color, icon=icon)
            login(request, user)
            messages.success(request, f'Welcome to GoalAchiever, {user.first_name}! 🎉')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'tracker/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    return render(request, 'tracker/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out. See you soon! 👋')
    return redirect('landing')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.now().date()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    habits = Habit.objects.filter(user=request.user, is_active=True, is_archived=False)

    today_habits = []
    for habit in habits:
        if not habit.is_due_on(today):
            continue
        log = HabitLog.objects.filter(habit=habit, date=today).first()
        today_habits.append({
            'habit': habit,
            'completed': log.completed if log else False,
            'log': log,
        })

    completed_today = sum(1 for h in today_habits if h['completed'])
    total_today = len(today_habits)
    completion_pct = int((completed_today / total_today * 100)) if total_today else 0

    # Weekly stats (last 7 days)
    weekly_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        total = habits.count()
        done = HabitLog.objects.filter(habit__in=habits, date=d, completed=True).count()
        weekly_data.append({'day': d.strftime('%a'), 'done': done, 'total': total})

    # Heatmap data (last 90 days)
    heatmap_data = {}
    for i in range(89, -1, -1):
        d = today - timedelta(days=i)
        count = HabitLog.objects.filter(habit__in=habits, date=d, completed=True).count()
        heatmap_data[str(d)] = count

    # Top streaks
    top_habits = habits.order_by('-current_streak')[:3]

    # Recent badges
    recent_badges = UserBadge.objects.filter(user=request.user).select_related('badge').order_by('-earned_at')[:3]

    # Reminder alarms data for JS
    reminder_habits = []
    for h in habits:
        if h.reminder_time:
            reminder_habits.append({
                'id': h.pk,
                'name': h.name,
                'reminder_time': h.reminder_time.strftime('%H:%M'),
            })

    # Pending (not completed) habits for alert banner
    pending_habits = [item['habit'].name for item in today_habits if not item['completed']]

    # Streak freeze candidates (habits due yesterday that were missed and user has freezes)
    yesterday = today - timedelta(days=1)
    freeze_candidates = []
    for habit in habits:
        if not habit.is_due_on(yesterday):
            continue
        log = habit.logs.filter(date=yesterday).first()
        if (not log or not log.completed) and (not log or not log.streak_frozen):
            freeze_candidates.append(habit.pk)

    context = {
        'profile': profile,
        'today_habits': today_habits,
        'completed_today': completed_today,
        'total_today': total_today,
        'completion_pct': completion_pct,
        'weekly_data': json.dumps(weekly_data),
        'heatmap_data': json.dumps(heatmap_data),
        'top_habits': top_habits,
        'recent_badges': recent_badges,
        'total_habits': habits.count(),
        'today': today,
        'reminder_habits': json.dumps(reminder_habits),
        'reminder_habits_list': reminder_habits,
        'pending_habits': pending_habits,
        'freeze_candidates': freeze_candidates,
        'streak_freezes': profile.streak_freezes,
    }
    return render(request, 'tracker/dashboard.html', context)


# ─── Habit CRUD ──────────────────────────────────────────────────────────────

@login_required
def habit_list(request):
    habits = Habit.objects.filter(user=request.user, is_archived=False)
    categories = Category.objects.filter(user=request.user)
    category_filter = request.GET.get('category', '')
    freq_filter = request.GET.get('frequency', '')
    search = request.GET.get('search', '')

    if category_filter:
        habits = habits.filter(category__id=category_filter)
    if freq_filter:
        habits = habits.filter(frequency=freq_filter)
    if search:
        habits = habits.filter(Q(name__icontains=search) | Q(description__icontains=search))

    today = timezone.now().date()
    habit_data = []
    for habit in habits:
        log = HabitLog.objects.filter(habit=habit, date=today).first()
        habit_data.append({'habit': habit, 'completed_today': log.completed if log else False})

    context = {
        'habit_data': habit_data,
        'categories': categories,
        'category_filter': category_filter,
        'freq_filter': freq_filter,
        'search': search,
    }
    return render(request, 'tracker/habit_list.html', context)


@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.user, request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, f'Habit "{habit.name}" created! 🎯')
            _check_badges(request.user)
            return redirect('habit_list')
    else:
        form = HabitForm(request.user)
    return render(request, 'tracker/habit_form.html', {'form': form, 'title': 'Create New Habit', 'action': 'Create'})


@login_required
def habit_edit(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        form = HabitForm(request.user, request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, f'Habit "{habit.name}" updated! ✏️')
            return redirect('habit_detail', pk=pk)
    else:
        form = HabitForm(request.user, instance=habit)
    return render(request, 'tracker/habit_form.html', {'form': form, 'title': 'Edit Habit', 'action': 'Save Changes', 'habit': habit})


@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        name = habit.name
        habit.delete()
        messages.success(request, f'Habit "{name}" deleted.')
        return redirect('habit_list')
    return render(request, 'tracker/habit_confirm_delete.html', {'habit': habit})


@login_required
def habit_detail(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.now().date()
    log_form = HabitLogNoteForm()

    if request.method == 'POST':
        log_form = HabitLogNoteForm(request.POST)
        if log_form.is_valid():
            log, _ = HabitLog.objects.get_or_create(habit=habit, date=today)
            log.note = log_form.cleaned_data['note']
            log.mood = log_form.cleaned_data['mood']
            log.save()
            messages.success(request, 'Check-in saved! ✅')
            return redirect('habit_detail', pk=pk)

    # Last 30 logs
    logs = habit.logs.filter(date__gte=today - timedelta(days=29)).order_by('date')

    # Chart data (last 30 days)
    chart_labels = []
    chart_data = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        log = habit.logs.filter(date=d).first()
        chart_labels.append(d.strftime('%b %d'))
        chart_data.append(1 if (log and log.completed) else 0)

    last_7 = habit.get_last_7_days_status()

    context = {
        'habit': habit,
        'logs': logs,
        'last_7': last_7,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'log_form': log_form,
        'today': today,
        'due_today': habit.is_due_on(today),
        'completed_today': habit.is_completed_today(),
    }
    return render(request, 'tracker/habit_detail.html', context)


@login_required
def toggle_habit(request, pk):
    """AJAX: Toggle habit completion for today."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.now().date()
    if not habit.is_due_on(today):
        return JsonResponse({'error': 'This habit is not due today.'}, status=400)
    log, created = HabitLog.objects.get_or_create(habit=habit, date=today)

    if created or not log.completed:
        xp_earned = _award_completion(request.user, habit, log, today)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        return JsonResponse({
            'status': 'completed',
            'streak': habit.current_streak,
            'xp_earned': xp_earned,
            'total_xp': profile.xp_points,
            'level': profile.level,
            'message': f'+{xp_earned} XP earned! 🎉'
        })
    else:
        log.completed = False
        log.completed_at = None
        log.save()
        habit.total_completions = max(0, habit.total_completions - 1)
        habit.update_streak()

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        xp_earned = habit.get_xp_reward()
        profile.xp_points = max(0, profile.xp_points - xp_earned)
        profile.total_habits_completed = max(0, profile.total_habits_completed - 1)
        profile.update_level()
        profile.save()

        return JsonResponse({
            'status': 'uncompleted',
            'streak': habit.current_streak,
            'message': 'Habit unmarked.'
        })


@login_required
def archive_habit(request, pk):
    if request.method != 'POST':
        return redirect('habit_list')
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit.is_archived = not habit.is_archived
    habit.save()
    action = 'archived' if habit.is_archived else 'unarchived'
    messages.success(request, f'Habit "{habit.name}" {action}.')
    return redirect('habit_list')


# ─── Category Views ───────────────────────────────────────────────────────────

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user).annotate(habit_count=Count('habits'))
    form = CategoryForm()
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, f'Category "{cat.name}" created! 📁')
            return redirect('category_list')
    return render(request, 'tracker/category_list.html', {'categories': categories, 'form': form})


@login_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Category deleted.')
        return redirect('category_list')
    return render(request, 'tracker/category_confirm_delete.html', {'category': cat})


# ─── Analytics ───────────────────────────────────────────────────────────────

@login_required
def analytics(request):
    today = timezone.now().date()
    habits = Habit.objects.filter(user=request.user, is_archived=False)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Overall stats
    total_completions = HabitLog.objects.filter(habit__in=habits, completed=True).count()
    total_logs = HabitLog.objects.filter(habit__in=habits).count()
    overall_rate = int((total_completions / total_logs * 100)) if total_logs else 0

    # Last 30 days chart
    daily_labels, daily_completions = [], []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        count = HabitLog.objects.filter(habit__in=habits, date=d, completed=True).count()
        daily_labels.append(d.strftime('%b %d'))
        daily_completions.append(count)

    # Per-habit completion rates
    habit_names, habit_rates = [], []
    for h in habits:
        habit_names.append(h.name)
        habit_rates.append(h.completion_rate())

    # Category distribution
    cat_names, cat_counts = [], []
    for cat in Category.objects.filter(user=request.user):
        count = HabitLog.objects.filter(habit__category=cat, completed=True).count()
        if count > 0:
            cat_names.append(cat.name)
            cat_counts.append(count)

    # Best performing habits
    best_habits = sorted(habits, key=lambda h: h.completion_rate(), reverse=True)[:5]

    context = {
        'profile': profile,
        'total_completions': total_completions,
        'overall_rate': overall_rate,
        'total_habits': habits.count(),
        'daily_labels': json.dumps(daily_labels),
        'daily_completions': json.dumps(daily_completions),
        'habit_names': json.dumps(habit_names),
        'habit_rates': json.dumps(habit_rates),
        'cat_names': json.dumps(cat_names),
        'cat_counts': json.dumps(cat_counts),
        'best_habits': best_habits,
    }
    return render(request, 'tracker/analytics.html', context)


# ─── Profile ─────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    habits = Habit.objects.filter(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            form.save()
            messages.success(request, 'Profile updated! ✅')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    context = {'profile': profile, 'form': form, 'badges': badges, 'habits': habits}
    return render(request, 'tracker/profile.html', context)


# ─── Archived Habits ──────────────────────────────────────────────────────────

@login_required
def archived_habits(request):
    habits = Habit.objects.filter(user=request.user, is_archived=True)
    return render(request, 'tracker/archived.html', {'habits': habits})


# ─── Badge Helper ─────────────────────────────────────────────────────────────

def _perfect_period(user, days):
    """True only if every day that had a due habit in the period was fully completed."""
    today = timezone.now().date()
    habits = Habit.objects.filter(user=user, is_archived=False, is_active=True)
    due_days = 0
    for i in range(days):
        d = today - timedelta(days=i)
        due_habits = [h for h in habits if h.is_due_on(d) and h.start_date <= d]
        if not due_habits:
            continue
        due_days += 1
        completed = HabitLog.objects.filter(habit__in=due_habits, date=d, completed=True).count()
        if completed != len(due_habits):
            return False
    return due_days > 0


def _check_badges(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    habits = Habit.objects.filter(user=user)
    total_completions = HabitLog.objects.filter(habit__in=habits, completed=True).count()
    all_badges = Badge.objects.all()

    for badge in all_badges:
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            continue
        earned = False
        bt = badge.badge_type
        if bt == 'streak_7' and any(h.current_streak >= 7 for h in habits):
            earned = True
        elif bt == 'streak_30' and any(h.current_streak >= 30 for h in habits):
            earned = True
        elif bt == 'streak_100' and any(h.current_streak >= 100 for h in habits):
            earned = True
        elif bt == 'habits_5' and habits.count() >= 5:
            earned = True
        elif bt == 'habits_10' and habits.count() >= 10:
            earned = True
        elif bt == 'completions_50' and total_completions >= 50:
            earned = True
        elif bt == 'completions_100' and total_completions >= 100:
            earned = True
        elif bt == 'level_5' and profile.level >= 5:
            earned = True
        elif bt == 'level_10' and profile.level >= 10:
            earned = True
        elif bt == 'perfect_week':
            earned = _perfect_period(user, 7)
        elif bt == 'perfect_month':
            earned = _perfect_period(user, 30)
        elif bt == 'early_bird' and HabitLog.objects.filter(habit__in=habits, completed=True, completed_at__hour__lt=8).exists():
            earned = True
        elif bt == 'night_owl' and HabitLog.objects.filter(habit__in=habits, completed=True, completed_at__hour__gte=22).exists():
            earned = True
        if earned:
            UserBadge.objects.create(user=user, badge=badge)


def _award_completion(user, habit, log, day, note=''):
    """Mark a habit log completed and award XP/streak/badges consistently."""
    log.completed = True
    log.completed_at = timezone.now()
    if note:
        log.note = note
    log.save()
    habit.total_completions += 1
    habit.update_streak()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    xp_earned = habit.get_xp_reward()
    profile.xp_points += xp_earned
    profile.total_habits_completed += 1
    if habit.current_streak > profile.longest_streak:
        profile.longest_streak = habit.current_streak
    profile.update_level()
    profile.save()
    _check_badges(user)
    return xp_earned


# ─── Streak Freeze ───────────────────────────────────────────────────────────

@login_required
def use_streak_freeze(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    if profile.streak_freezes <= 0:
        return JsonResponse({'error': 'No streak freezes remaining.'}, status=400)

    if not habit.is_due_on(yesterday):
        return JsonResponse({'error': 'Yesterday was not a due day for this habit.'}, status=400)

    log, created = HabitLog.objects.get_or_create(habit=habit, date=yesterday)
    if log.completed:
        return JsonResponse({'error': 'Habit was already completed yesterday.'}, status=400)
    if log.streak_frozen:
        return JsonResponse({'error': 'Streak freeze already applied to yesterday.'}, status=400)

    log.streak_frozen = True
    log.save()
    habit.update_streak()

    profile.streak_freezes -= 1
    if habit.current_streak > profile.longest_streak:
        profile.longest_streak = habit.current_streak
    profile.save()

    return JsonResponse({
        'status': 'freeze_applied',
        'streak': habit.current_streak,
        'freezes_remaining': profile.streak_freezes,
        'message': f'Streak freeze used! Streak preserved at {habit.current_streak} days. ❄️',
    })


# ─── Calendar View ───────────────────────────────────────────────────────────

@login_required
def calendar_view(request):
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    num_days = monthrange(year, month)[1]
    first_day = date(year, month, 1)
    last_day = date(year, month, num_days)
    weekday_offset = first_day.weekday()

    habits = Habit.objects.filter(user=request.user, is_active=True, is_archived=False)

    calendar_days = []
    for i in range(1, num_days + 1):
        d = date(year, month, i)
        due_habits = [h for h in habits if h.is_due_on(d) and h.start_date <= d]
        completed = 0
        frozen = 0
        total = len(due_habits)
        for h in due_habits:
            log = h.logs.filter(date=d).first()
            if log:
                if log.completed:
                    completed += 1
                elif log.streak_frozen:
                    frozen += 1
        if total == 0:
            status = 'none'
        elif completed == total:
            status = 'perfect'
        elif completed + frozen >= total:
            status = 'frozen'
        elif completed > 0:
            status = 'partial'
        else:
            status = 'missed'
        calendar_days.append({'day': i, 'date': d, 'status': status,
                              'completed': completed, 'frozen': frozen, 'total': total})

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_name = date(year, month, 1).strftime('%B %Y')

    context = {
        'calendar_days': calendar_days,
        'month_name': month_name,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'weekday_offset': weekday_offset,
        'today': today,
        'habits': habits,
    }
    return render(request, 'tracker/calendar.html', context)


# ─── Strava API Integration ───────────────────────────────────────────────────

STRAVA_TERMS = ['run', 'walk', 'ride', 'fitness', 'exercise', 'workout', 'step', 'sport']

@login_required
def strava_connect(request):
    client_id = getattr(settings, 'STRAVA_CLIENT_ID', '')
    if (not client_id or client_id == 'your_strava_client_id'
            or getattr(settings, 'STRAVA_MOCK', False)):
        return redirect('strava_mock_authorize')

    redirect_uri = request.build_absolute_uri('/strava/callback/')
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'approval_prompt': 'auto',
        'scope': 'read,activity:read_all',
    }
    url = f"https://www.strava.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    return redirect(url)


@login_required
def strava_callback(request):
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error or not code:
        messages.error(request, f'Strava connection canceled or failed: {error or "No authorization code."}')
        return redirect('profile')
        
    client_id = getattr(settings, 'STRAVA_CLIENT_ID', '')
    client_secret = getattr(settings, 'STRAVA_CLIENT_SECRET', '')
    
    try:
        res = requests.post('https://www.strava.com/oauth/token', data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }, timeout=10)
        data = res.json()
        
        if 'access_token' in data:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.strava_access_token = data['access_token']
            profile.strava_refresh_token = data.get('refresh_token', '')
            profile.strava_token_expires_at = data.get('expires_at', 0)
            if 'athlete' in data:
                profile.strava_athlete_id = str(data['athlete'].get('id', ''))
            profile.save()
            messages.success(request, 'Successfully connected your Strava account! 🎉')
        else:
            messages.error(request, f'Failed to obtain Strava tokens: {data.get("message", "Unknown error")}')
    except Exception as e:
        messages.error(request, f'Error connecting to Strava: {str(e)}')

    return redirect('profile')


@login_required
def strava_sync(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.strava_access_token:
        messages.warning(request, 'Please connect your Strava account first.')
        return redirect('profile')

    if profile.strava_access_token == 'mock_token':
        synced = 0
        today = timezone.now().date()
        for habit in Habit.objects.filter(user=request.user, is_active=True):
            if any(term in habit.name.lower() for term in STRAVA_TERMS):
                log, _ = HabitLog.objects.get_or_create(habit=habit, date=today)
                if not log.completed:
                    _award_completion(request.user, habit, log, today,
                                      'Synced from Mock Strava: Test Run (Run, 5.0km)')
                    synced += 1
        messages.success(request, f'Mock sync complete! Updated {synced} habit completions. 🚴')
        return redirect('profile')

    client_id = getattr(settings, 'STRAVA_CLIENT_ID', '')
    client_secret = getattr(settings, 'STRAVA_CLIENT_SECRET', '')
    
    # Check token expiration & refresh if needed
    import time
    if profile.strava_token_expires_at and profile.strava_token_expires_at < time.time():
        try:
            res = requests.post('https://www.strava.com/oauth/token', data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': profile.strava_refresh_token,
            }, timeout=10)
            data = res.json()
            if 'access_token' in data:
                profile.strava_access_token = data['access_token']
                profile.strava_refresh_token = data.get('refresh_token', profile.strava_refresh_token)
                profile.strava_token_expires_at = data.get('expires_at', profile.strava_token_expires_at)
                profile.save()
        except Exception as e:
            messages.error(request, f'Failed to refresh Strava token: {str(e)}')
            return redirect('profile')

    # Fetch recent activities
    headers = {'Authorization': f'Bearer {profile.strava_access_token}'}
    try:
        res = requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=30', headers=headers, timeout=10)
        if res.status_code != 200:
            messages.error(request, f'Strava API returned status {res.status_code}')
            return redirect('profile')
            
        activities = res.json()
        synced_count = 0
        
        user_habits = Habit.objects.filter(user=request.user, is_active=True)
        
        for act in activities:
            start_date_str = act.get('start_date_local', '')[:10]
            if not start_date_str:
                continue
            act_date = date.fromisoformat(start_date_str)
            act_name = act.get('name', 'Strava Activity')
            act_type = act.get('type', 'Workout')
            distance_km = round(act.get('distance', 0) / 1000, 2)
            
            for habit in user_habits:
                h_name_lower = habit.name.lower()
                if any(term in h_name_lower for term in STRAVA_TERMS) or act_type.lower() in h_name_lower:
                    log, created = HabitLog.objects.get_or_create(habit=habit, date=act_date)
                    if not log.completed:
                        _award_completion(
                            request.user, habit, log, act_date,
                            f"Synced from Strava: {act_name} ({act_type}, {distance_km}km)",
                        )
                        synced_count += 1
                        
        messages.success(request, f'Synced {len(activities)} Strava activities! Updated {synced_count} habit completions. 🚴‍♂️🏃')
    except Exception as e:
        messages.error(request, f'Error syncing Strava activities: {str(e)}')
        
    return redirect('profile')


# ─── Mock Strava (for local testing without real credentials) ───────────────

@login_required
def strava_mock_authorize(request):
    from django.http import HttpResponse
    from django.middleware.csrf import get_token
    csrf = get_token(request)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Mock Strava</title>
<style>
  body {{ font-family: Arial, sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#f5f5f5; }}
  .card {{ background:#fff; border-radius:12px; padding:40px; width:360px; text-align:center; box-shadow:0 4px 16px rgba(0,0,0,.1); }}
  .logo {{ font-size:40px; }}
  h2 {{ margin:12px 0 4px; }}
  p {{ color:#666; font-size:14px; }}
  .btn {{ display:inline-block; margin-top:20px; background:#fc4c02; color:#fff; border:none; padding:12px 28px; border-radius:8px; font-size:15px; cursor:pointer; text-decoration:none; }}
  .btn:hover {{ background:#e04400; }}
</style></head><body>
  <div class="card">
    <div class="logo">🏃</div>
    <h2>Mock Strava</h2>
    <p>This is a local test page simulating the Strava OAuth screen.<br>No real credentials are needed.</p>
    <form method="post" action="/strava/mock/callback/">
      <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
      <button type="submit" class="btn">Authorize</button>
    </form>
  </div>
</body></html>"""
    return HttpResponse(html)


@login_required
def strava_mock_callback(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.strava_access_token = 'mock_token'
    profile.strava_refresh_token = 'mock_refresh'
    profile.strava_token_expires_at = int(time.time()) + 86400 * 30
    profile.strava_athlete_id = 'mock_athlete_123'
    profile.save()
    messages.success(request, 'Connected to Mock Strava for testing! 🎉')
    return redirect('profile')


# ─── Spotify API Integration ────────────────────────────────────────────────

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'
MUSIC_TERMS = ['music', 'listen', 'song', 'podcast', 'audio', 'spotify', 'practice', 'guitar', 'piano', 'drums', 'sing']


def spotify_refresh_access_token(profile):
    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    client_secret = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')
    res = requests.post(SPOTIFY_TOKEN_URL, data={
        'grant_type': 'refresh_token',
        'refresh_token': profile.spotify_refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
    }, timeout=10)
    data = res.json()
    if 'access_token' in data:
        profile.spotify_access_token = data['access_token']
        profile.spotify_token_expires_at = int(time.time()) + data.get('expires_in', 3600)
        profile.save()
        return True
    return False


@login_required
def spotify_connect(request):
    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    if (not client_id or client_id == 'your_spotify_client_id'
            or getattr(settings, 'SPOTIFY_MOCK', False)):
        return redirect('spotify_mock_authorize')

    redirect_uri = request.build_absolute_uri('/spotify/callback/')
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': 'user-read-recently-played user-read-playback-state user-modify-playback-state user-read-currently-playing streaming',
    }
    url = f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(url)


@login_required
def spotify_callback(request):
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error or not code:
        messages.error(request, f'Spotify connection canceled or failed: {error or "No authorization code."}')
        return redirect('profile')

    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    client_secret = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')
    redirect_uri = request.build_absolute_uri('/spotify/callback/')

    try:
        res = requests.post(SPOTIFY_TOKEN_URL, data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        }, timeout=10)
        data = res.json()

        if 'access_token' in data:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.spotify_access_token = data['access_token']
            profile.spotify_refresh_token = data.get('refresh_token', '')
            profile.spotify_token_expires_at = int(time.time()) + data.get('expires_in', 3600)
            try:
                me = requests.get(f'{SPOTIFY_API_URL}/me',
                                  headers={'Authorization': f"Bearer {profile.spotify_access_token}"},
                                  timeout=10).json()
                profile.spotify_user_id = me.get('id') or me.get('display_name') or ''
            except Exception:
                pass
            profile.save()
            messages.success(request, 'Successfully connected your Spotify account! 🎧')
        else:
            messages.error(request, f'Failed to obtain Spotify tokens: {data.get("error_description", "Unknown error")}')
    except Exception as e:
        messages.error(request, f'Error connecting to Spotify: {str(e)}')

    return redirect('profile')


def _complete_matching_habits(user, date, note, terms):
    synced = 0
    for habit in Habit.objects.filter(user=user, is_active=True):
        if any(term in habit.name.lower() for term in terms):
            log, _ = HabitLog.objects.get_or_create(habit=habit, date=date)
            if not log.completed:
                _award_completion(user, habit, log, date, note)
                synced += 1
    return synced


@login_required
def spotify_sync(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.spotify_access_token:
        messages.warning(request, 'Please connect your Spotify account first.')
        return redirect('profile')

    # Mock mode
    if profile.spotify_access_token == 'mock_token':
        today = timezone.now().date()
        synced = _complete_matching_habits(
            request.user, today,
            'Synced from Mock Spotify: Top Songs 2026 (Pop, 3:45 min)',
            MUSIC_TERMS,
        )
        messages.success(request, f'Mock sync complete! Updated {synced} habit completions. 🎧')
        return redirect('profile')

    # Refresh token if expired
    if profile.spotify_token_expires_at and profile.spotify_token_expires_at < time.time():
        try:
            if not spotify_refresh_access_token(profile):
                messages.error(request, 'Failed to refresh Spotify token. Please reconnect.')
                return redirect('profile')
        except Exception as e:
            messages.error(request, f'Failed to refresh Spotify token: {str(e)}')
            return redirect('profile')

    headers = {'Authorization': f"Bearer {profile.spotify_access_token}"}
    try:
        res = requests.get(f'{SPOTIFY_API_URL}/me/player/recently-played?limit=50', headers=headers, timeout=10)
        if res.status_code != 200:
            messages.error(request, f'Spotify API returned status {res.status_code}')
            return redirect('profile')

        items = res.json().get('items', [])
        synced_count = 0
        for item in items:
            played_at = item.get('played_at', '')
            if not played_at:
                continue
            played_date = played_at[:10]
            try:
                played_date = date.fromisoformat(played_date)
            except ValueError:
                continue
            track = item.get('track', {})
            track_name = track.get('name', 'Track')
            artists = ', '.join(a.get('name', '') for a in track.get('artists', [])[:2])
            note = f"Synced from Spotify: {track_name} by {artists}"
            synced_count += _complete_matching_habits(request.user, played_date, note, MUSIC_TERMS)

        messages.success(request, f'Synced {len(items)} Spotify plays! Updated {synced_count} habit completions. 🎧🎵')
    except Exception as e:
        messages.error(request, f'Error syncing Spotify: {str(e)}')

    return redirect('profile')


# ─── Mock Spotify (for local testing without real credentials) ──────────────

@login_required
def spotify_mock_authorize(request):
    from django.http import HttpResponse
    from django.middleware.csrf import get_token
    csrf = get_token(request)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Mock Spotify</title>
<style>
  body {{ font-family: Arial, sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#121212; }}
  .card {{ background:#181818; border-radius:12px; padding:40px; width:360px; text-align:center; box-shadow:0 4px 16px rgba(0,0,0,.5); }}
  .logo {{ font-size:40px; }}
  h2 {{ margin:12px 0 4px; color:#fff; }}
  p {{ color:#b3b3b3; font-size:14px; }}
  .btn {{ display:inline-block; margin-top:20px; background:#1DB954; color:#fff; border:none; padding:12px 28px; border-radius:24px; font-size:15px; cursor:pointer; text-decoration:none; font-weight:bold; }}
  .btn:hover {{ background:#1ed760; }}
</style></head><body>
  <div class="card">
    <div class="logo">🎧</div>
    <h2>Mock Spotify</h2>
    <p>This is a local test page simulating the Spotify OAuth screen.<br>No real credentials are needed.</p>
    <form method="post" action="/spotify/mock/callback/">
      <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
      <button type="submit" class="btn">Authorize</button>
    </form>
  </div>
</body></html>"""
    return HttpResponse(html)


@login_required
def spotify_mock_callback(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.spotify_user_id = 'mock_user_123'
    profile.spotify_access_token = 'mock_token'
    profile.spotify_refresh_token = 'mock_refresh'
    profile.spotify_token_expires_at = int(time.time()) + 86400 * 30
    profile.save()
    messages.success(request, 'Connected to Mock Spotify for testing! 🎉')
    return redirect('profile')


def _to_spotify_embed_url(raw):
    raw = (raw or '').strip()
    if not raw:
        return ''
    m = re.search(r'open\.spotify\.com/embed/(track|album|playlist|artist|show|episode)/([A-Za-z0-9]+)', raw)
    if m:
        return f'https://open.spotify.com/embed/{m.group(1)}/{m.group(2)}'
    m = re.search(r'(?:open\.spotify\.com/|spotify:)(track|album|playlist|artist|show|episode)[/:]([A-Za-z0-9]+)', raw)
    if m:
        return f'https://open.spotify.com/embed/{m.group(1)}/{m.group(2)}'
    if re.fullmatch(r'[A-Za-z0-9]{22}', raw):
        return f'https://open.spotify.com/embed/track/{raw}'
    return ''


@login_required
def spotify_player_save(request):
    if request.method == 'POST':
        embed = _to_spotify_embed_url(request.POST.get('spotify_link', ''))
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.spotify_embed_url = embed
        profile.save()
        if embed:
            messages.success(request, 'Player updated! 🎵')
        else:
            messages.error(request, "Couldn't recognize that Spotify link. Paste a full Spotify track/playlist/album link.")
    return redirect('profile')


MOCK_TRACKS = [
    {'id': 'mock1', 'name': 'Blinding Lights', 'artists': 'The Weeknd', 'uri': 'spotify:track:mock1', 'image': ''},
    {'id': 'mock2', 'name': 'Levitating', 'artists': 'Dua Lipa', 'uri': 'spotify:track:mock2', 'image': ''},
    {'id': 'mock3', 'name': 'As It Was', 'artists': 'Harry Styles', 'uri': 'spotify:track:mock3', 'image': ''},
    {'id': 'mock4', 'name': 'Heat Waves', 'artists': 'Glass Animals', 'uri': 'spotify:track:mock4', 'image': ''},
    {'id': 'mock5', 'name': 'Save Your Tears', 'artists': 'The Weeknd', 'uri': 'spotify:track:mock5', 'image': ''},
]


@login_required
def spotify_token(request):
    """Return a valid Spotify access token for the Web Playback SDK (refreshing if needed)."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.spotify_access_token or profile.spotify_access_token == 'mock_token':
        return JsonResponse({'access_token': None, 'mock': True})

    if profile.spotify_token_expires_at and profile.spotify_token_expires_at < time.time():
        try:
            if not spotify_refresh_access_token(profile):
                return JsonResponse({'access_token': None, 'error': 'refresh_failed'}, status=401)
        except Exception:
            return JsonResponse({'access_token': None, 'error': 'refresh_failed'}, status=401)

    return JsonResponse({'access_token': profile.spotify_access_token, 'mock': False})


@login_required
def spotify_search(request):
    q = request.GET.get('q', '').strip()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not q:
        return JsonResponse({'tracks': []})

    if not profile.spotify_access_token or profile.spotify_access_token == 'mock_token':
        ql = q.lower()
        tracks = [t for t in MOCK_TRACKS if ql in t['name'].lower() or ql in t['artists'].lower()]
        return JsonResponse({'tracks': tracks[:10], 'mock': True})

    if profile.spotify_token_expires_at and profile.spotify_token_expires_at < time.time():
        try:
            if not spotify_refresh_access_token(profile):
                return JsonResponse({'tracks': [], 'error': 'refresh_failed'}, status=401)
        except Exception:
            return JsonResponse({'tracks': [], 'error': 'refresh_failed'}, status=401)

    try:
        headers = {'Authorization': f"Bearer {profile.spotify_access_token}"}
        res = requests.get(
            f'{SPOTIFY_API_URL}/search?q={urllib.parse.quote(q)}&type=track&limit=10',
            headers=headers, timeout=10)
        if res.status_code != 200:
            return JsonResponse({'tracks': [], 'error': f'status {res.status_code}'}, status=502)
        items = res.json().get('tracks', {}).get('items', [])
        tracks = [{
            'id': t.get('id'),
            'name': t.get('name'),
            'artists': ', '.join(a.get('name', '') for a in t.get('artists', [])[:2]),
            'uri': t.get('uri'),
            'image': t['album']['images'][0]['url'] if t.get('album', {}).get('images') else '',
        } for t in items]
        return JsonResponse({'tracks': tracks, 'mock': False})
    except Exception as e:
        return JsonResponse({'tracks': [], 'error': str(e)}, status=502)


@login_required
def spotify_play(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        body = {}
    device_id = body.get('device_id', '')
    uris = body.get('uris', [])

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.spotify_access_token or profile.spotify_access_token == 'mock_token':
        return JsonResponse({'success': True, 'mock': True})

    if profile.spotify_token_expires_at and profile.spotify_token_expires_at < time.time():
        try:
            if not spotify_refresh_access_token(profile):
                return JsonResponse({'success': False, 'error': 'Token refresh failed'}, status=401)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=401)

    try:
        headers = {'Authorization': f"Bearer {profile.spotify_access_token}", 'Content-Type': 'application/json'}
        url = f'{SPOTIFY_API_URL}/me/player/play'
        if device_id:
            url += f'?device_id={urllib.parse.quote(device_id)}'
        res = requests.put(url, headers=headers, data=json.dumps({'uris': uris}), timeout=10)
        if res.status_code in (200, 204):
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': f'Playback failed (status {res.status_code})'}, status=502)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=502)

