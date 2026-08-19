import csv
import os
import random
import math
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from tracker.models import Habit, HabitLog, Category, UserProfile

class Command(BaseCommand):
    help = 'Imports Kaggle Daily Habit Tracker dataset'

    def handle(self, *args, **options):
        dataset_path = 'dataset/Daily_Habit_Tracker.csv'
        if not os.path.exists(dataset_path):
            self.stdout.write(self.style.ERROR(f'Dataset not found at {dataset_path}'))
            return

        # Get or create an admin user
        user = User.objects.first()
        if not user:
            user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Created default admin user.'))
        
        # Ensure user has a profile
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)

        # Get or create a category
        category, _ = Category.objects.get_or_create(user=user, name='Health & Wellness', defaults={'icon': 'bi-heart-pulse', 'color': '#00b894'})

        # Create Habits
        habit_sleep, _ = Habit.objects.get_or_create(user=user, name='7+ Hours of Sleep', defaults={'category': category, 'target_days': 60, 'icon': 'bi-moon-stars'})
        habit_steps, _ = Habit.objects.get_or_create(user=user, name='10,000 Steps', defaults={'category': category, 'target_days': 60, 'icon': 'bi-lightning'})
        habit_water, _ = Habit.objects.get_or_create(user=user, name='Hydration (2L+)', defaults={'category': category, 'target_days': 60, 'icon': 'bi-droplet'})
        habit_study, _ = Habit.objects.get_or_create(user=user, name='Study Session (2h+)', defaults={'category': category, 'target_days': 60, 'icon': 'bi-book'})

        # Delete old logs for these habits to avoid clutter/errors
        HabitLog.objects.filter(habit__in=[habit_sleep, habit_steps, habit_water, habit_study]).delete()

        # Read CSV
        logs_to_create = []
        with open(dataset_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # We only want ~60 days of data to make the dashboard look dense and active.
        rows = rows[:60]
        
        today = timezone.now().date()
        
        for i, row in enumerate(rows):
            # Map backwards from today
            log_date = today - timedelta(days=59 - i)
            
            sleep_hours = float(row.get('Sleep_Hours', 0))
            steps = int(row.get('Steps', 0))
            water = int(row.get('Water_Intake_ml', 0))
            study = float(row.get('Study_Hours', 0))
            mood_10 = int(row.get('Mood_Score', 5))
            
            # Scale mood from 1-10 to 1-5
            mood_5 = max(1, min(5, math.ceil(mood_10 / 2)))

            # Sleep
            logs_to_create.append(HabitLog(
                habit=habit_sleep, date=log_date, completed=(sleep_hours >= 7),
                mood=mood_5, note=f"Slept {sleep_hours} hours."
            ))

            # Steps
            logs_to_create.append(HabitLog(
                habit=habit_steps, date=log_date, completed=(steps >= 10000),
                mood=mood_5, note=f"Walked {steps} steps."
            ))

            # Water
            logs_to_create.append(HabitLog(
                habit=habit_water, date=log_date, completed=(water >= 2000),
                mood=mood_5, note=f"Drank {water}ml of water."
            ))

            # Study
            logs_to_create.append(HabitLog(
                habit=habit_study, date=log_date, completed=(study >= 2),
                mood=mood_5, note=f"Studied for {study} hours."
            ))
            
        HabitLog.objects.bulk_create(logs_to_create)
        
        # Update habit stats (total_completions, streaks)
        for h in [habit_sleep, habit_steps, habit_water, habit_study]:
            h.total_completions = h.logs.filter(completed=True).count()
            h.update_streak()
            h.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {len(rows)} days of Kaggle data for 4 habits!'))
