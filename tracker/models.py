from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    xp_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    total_habits_completed = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    streak_freezes = models.IntegerField(default=3, help_text="Streak freeze tokens available")
    created_at = models.DateTimeField(auto_now_add=True)
    strava_athlete_id = models.CharField(max_length=50, blank=True, null=True)
    strava_access_token = models.CharField(max_length=255, blank=True, null=True)
    strava_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    strava_token_expires_at = models.IntegerField(blank=True, null=True)
    spotify_user_id = models.CharField(max_length=100, blank=True, null=True)
    spotify_access_token = models.CharField(max_length=255, blank=True, null=True)
    spotify_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    spotify_token_expires_at = models.IntegerField(blank=True, null=True)
    spotify_embed_url = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_level_title(self):
        titles = {
            1: 'Beginner', 2: 'Starter', 3: 'Consistent', 4: 'Dedicated',
            5: 'Champion', 6: 'Expert', 7: 'Master', 8: 'Legend', 9: 'Grandmaster', 10: 'Elite'
        }
        return titles.get(min(self.level, 10), 'Elite')

    def xp_for_next_level(self):
        return self.level * 100

    def xp_progress_percent(self):
        needed = self.xp_for_next_level()
        current = self.xp_points % needed if needed else 0
        return int((current / needed) * 100) if needed else 0

    def update_level(self):
        new_level = max(1, self.xp_points // 100 + 1)
        if new_level != self.level:
            self.level = new_level
            self.save()


class Category(models.Model):
    COLOR_CHOICES = [
        ('#6c5ce7', 'Purple'), ('#00b894', 'Green'), ('#fd79a8', 'Pink'),
        ('#fdcb6e', 'Yellow'), ('#0984e3', 'Blue'), ('#e17055', 'Orange'),
        ('#a29bfe', 'Lavender'), ('#55efc4', 'Mint'),
    ]
    ICON_CHOICES = [
        ('bi-heart-pulse', 'Health'), ('bi-book', 'Learning'), ('bi-lightning', 'Fitness'),
        ('bi-piggy-bank', 'Finance'), ('bi-emoji-smile', 'Mindfulness'),
        ('bi-people', 'Social'), ('bi-briefcase', 'Work'), ('bi-stars', 'Personal'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='#6c5ce7')
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, default='bi-stars')

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('weekdays', 'Weekdays Only'),
        ('weekends', 'Weekends Only'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='habits')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    target_days = models.IntegerField(default=30, help_text="Target number of days to complete")
    reminder_time = models.TimeField(null=True, blank=True)
    color = models.CharField(max_length=10, default='#6c5ce7')
    icon = models.CharField(max_length=50, default='bi-check-circle')
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    total_completions = models.IntegerField(default=0)
    xp_reward = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(default=date.today)

    def __str__(self):
        return self.name

    def get_xp_reward(self):
        multiplier = {'easy': 1, 'medium': 1.5, 'hard': 2}
        return int(self.xp_reward * multiplier.get(self.difficulty, 1))

    def is_completed_today(self):
        today = timezone.now().date()
        return self.logs.filter(date=today, completed=True).exists()

    def is_due_on(self, day):
        if self.frequency == 'weekdays':
            return day.weekday() < 5
        if self.frequency == 'weekends':
            return day.weekday() >= 5
        if self.frequency == 'weekly':
            return day.weekday() == self.start_date.weekday()
        return True

    def completion_rate(self):
        total = self.logs.count()
        if total == 0:
            return 0
        completed = self.logs.filter(completed=True).count()
        return int((completed / total) * 100)

    def days_since_start(self):
        return (date.today() - self.start_date).days + 1

    def progress_percent(self):
        if self.target_days == 0:
            return 0
        return min(int((self.total_completions / self.target_days) * 100), 100)

    def get_last_7_days_status(self):
        today = timezone.now().date()
        result = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            log = self.logs.filter(date=day).first()
            result.append({
                'date': day,
                'completed': log.completed if log else False,
                'day_name': day.strftime('%a'),
            })
        return result

    def update_streak(self):
        today = timezone.now().date()
        streak = 0

        if self.frequency == 'weekly':
            anchor_wd = self.start_date.weekday()
            anchor = today - timedelta(days=(today.weekday() - anchor_wd) % 7)
            if anchor > today:
                anchor -= timedelta(days=7)
            if not self.logs.filter(date=anchor, completed=True).exists():
                self.current_streak = 0
                self.save()
                return
            day = anchor
            while True:
                log = self.logs.filter(date=day).first()
                if log and (log.completed or log.streak_frozen):
                    streak += 1
                    day -= timedelta(days=7)
                else:
                    break
        else:
            log_today = self.logs.filter(date=today).first()
            log_yesterday = self.logs.filter(date=today - timedelta(days=1)).first()
            if log_today and (log_today.completed or log_today.streak_frozen):
                day = today
            elif log_yesterday and (log_yesterday.completed or log_yesterday.streak_frozen):
                day = today - timedelta(days=1)
            else:
                self.current_streak = 0
                self.save()
                return

            while True:
                log = self.logs.filter(date=day).first()
                if log and (log.completed or log.streak_frozen):
                    streak += 1
                    day -= timedelta(days=1)
                else:
                    break

        self.current_streak = streak
        if streak > self.best_streak:
            self.best_streak = streak
        self.save()


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(default=date.today)
    completed = models.BooleanField(default=False)
    streak_frozen = models.BooleanField(default=False, help_text="Day preserved by a streak freeze")
    note = models.TextField(blank=True)
    mood = models.IntegerField(default=3, help_text="1-5 mood rating")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['habit', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.name} - {self.date} - {'✓' if self.completed else '✗'}"


class Badge(models.Model):
    BADGE_TYPES = [
        ('streak_7', '7-Day Streak'), ('streak_30', '30-Day Streak'), ('streak_100', '100-Day Streak'),
        ('habits_5', '5 Habits Created'), ('habits_10', '10 Habits Created'),
        ('completions_50', '50 Completions'), ('completions_100', '100 Completions'),
        ('perfect_week', 'Perfect Week'), ('perfect_month', 'Perfect Month'),
        ('level_5', 'Reached Level 5'), ('level_10', 'Reached Level 10'),
        ('early_bird', 'Early Bird'), ('night_owl', 'Night Owl'),
    ]
    BADGE_ICONS = {
        'streak_7': 'bi-fire', 'streak_30': 'bi-stars', 'streak_100': 'bi-trophy',
        'habits_5': 'bi-collection', 'habits_10': 'bi-grid-3x3-gap',
        'completions_50': 'bi-check2-all', 'completions_100': 'bi-award',
        'perfect_week': 'bi-calendar-check', 'perfect_month': 'bi-calendar2-check',
        'level_5': 'bi-star-fill', 'level_10': 'bi-gem',
        'early_bird': 'bi-sunrise', 'night_owl': 'bi-moon-stars',
    }
    BADGE_COLORS = {
        'streak_7': '#fdcb6e', 'streak_30': '#e17055', 'streak_100': '#d63031',
        'habits_5': '#00b894', 'habits_10': '#00cec9',
        'completions_50': '#0984e3', 'completions_100': '#6c5ce7',
        'perfect_week': '#fd79a8', 'perfect_month': '#a29bfe',
        'level_5': '#fdcb6e', 'level_10': '#ffd700',
        'early_bird': '#f9ca24', 'night_owl': '#6c5ce7',
    }
    name = models.CharField(max_length=100)
    badge_type = models.CharField(max_length=50, choices=BADGE_TYPES, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name

    def get_icon(self):
        return self.BADGE_ICONS.get(self.badge_type, 'bi-award')

    def get_color(self):
        return self.BADGE_COLORS.get(self.badge_type, '#6c5ce7')


class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'badge']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"
