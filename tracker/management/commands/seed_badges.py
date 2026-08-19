from django.core.management.base import BaseCommand
from tracker.models import Badge


class Command(BaseCommand):
    help = 'Seed default badges into the database'

    def handle(self, *args, **kwargs):
        badges = [
            ('7-Day Streak', 'streak_7', 'Maintain a 7-day streak on any habit'),
            ('30-Day Streak', 'streak_30', 'Maintain a 30-day streak on any habit'),
            ('100-Day Streak', 'streak_100', 'Maintain a 100-day streak on any habit'),
            ('5 Habits', 'habits_5', 'Create 5 or more habits'),
            ('10 Habits', 'habits_10', 'Create 10 or more habits'),
            ('50 Completions', 'completions_50', 'Complete habits 50 times total'),
            ('100 Completions', 'completions_100', 'Complete habits 100 times total'),
            ('Perfect Week', 'perfect_week', 'Complete all habits every day for a week'),
            ('Perfect Month', 'perfect_month', 'Complete all habits every day for a month'),
            ('Level 5 Reached', 'level_5', 'Reach level 5'),
            ('Level 10 Reached', 'level_10', 'Reach level 10'),
            ('Early Bird', 'early_bird', 'Complete a habit before 8am'),
            ('Night Owl', 'night_owl', 'Complete a habit after 10pm'),
        ]
        created = 0
        for name, badge_type, desc in badges:
            _, made = Badge.objects.get_or_create(
                badge_type=badge_type,
                defaults={'name': name, 'description': desc}
            )
            if made:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} new badges ({len(badges)} total)'))
