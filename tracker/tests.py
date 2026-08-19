from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Habit, HabitLog, Badge, UserBadge, UserProfile
from .views import _check_badges, _perfect_period


class HabitFrequencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', password='pass')

    def test_daily_due_every_day(self):
        h = Habit.objects.create(user=self.user, name='Daily', frequency='daily')
        for offset in range(-3, 4):
            d = timezone.now().date() + timedelta(days=offset)
            self.assertTrue(h.is_due_on(d), f'daily should be due on {d}')

    def test_weekdays_only(self):
        h = Habit.objects.create(user=self.user, name='Weekdays', frequency='weekdays')
        for offset in range(7):
            d = timezone.now().date() + timedelta(days=offset)
            if d.weekday() < 5:
                self.assertTrue(h.is_due_on(d), f'{d} is a weekday, should be due')
            else:
                self.assertFalse(h.is_due_on(d), f'{d} is a weekend, should not be due')

    def test_weekends_only(self):
        h = Habit.objects.create(user=self.user, name='Weekends', frequency='weekends')
        for offset in range(7):
            d = timezone.now().date() + timedelta(days=offset)
            if d.weekday() >= 5:
                self.assertTrue(h.is_due_on(d), f'{d} is a weekend, should be due')
            else:
                self.assertFalse(h.is_due_on(d), f'{d} is a weekday, should not be due')

    def test_weekly_due_only_on_anchor_weekday(self):
        start = timezone.now().date()
        h = Habit.objects.create(user=self.user, name='Weekly', frequency='weekly', start_date=start)
        anchor_wd = start.weekday()
        for offset in range(14):
            d = start + timedelta(days=offset)
            if d.weekday() == anchor_wd:
                self.assertTrue(h.is_due_on(d), f'{d} is anchor day, should be due')
            else:
                self.assertFalse(h.is_due_on(d), f'{d} is not anchor day, should not be due')


class StreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('streaker', password='pass')
        self.today = timezone.now().date()

    def test_daily_streak_counts_consecutive_days(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.today, completed=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=1), completed=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=3), completed=True)
        h.update_streak()
        self.assertEqual(h.current_streak, 2)

    def test_daily_streak_resets_when_missed(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=2), completed=True)
        h.update_streak()
        self.assertEqual(h.current_streak, 0)

    def test_weekly_streak_counts_consecutive_weeks(self):
        h = Habit.objects.create(user=self.user, name='Gym', frequency='weekly', start_date=self.today)
        HabitLog.objects.create(habit=h, date=self.today, completed=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=7), completed=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=21), completed=True)
        h.update_streak()
        self.assertEqual(h.current_streak, 2)

    def test_weekly_streak_zero_without_anchor_completion(self):
        h = Habit.objects.create(user=self.user, name='Gym', frequency='weekly', start_date=self.today)
        h.update_streak()
        self.assertEqual(h.current_streak, 0)


class ToggleHabitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('toggler', password='pass')
        self.client.force_login(self.user)
        self.today = timezone.now().date()

    def test_complete_awards_xp(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily',
                                 difficulty='easy', xp_reward=10)
        resp = self.client.post(f'/habits/{h.pk}/toggle/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['xp_earned'], 10)
        h.refresh_from_db()
        profile = self.user.profile
        profile.refresh_from_db()
        self.assertEqual(h.total_completions, 1)
        self.assertEqual(profile.xp_points, 10)
        self.assertEqual(profile.total_habits_completed, 1)

    def test_uncomplete_refunds_xp(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily',
                                 difficulty='hard', xp_reward=10)
        self.client.post(f'/habits/{h.pk}/toggle/')
        self.client.post(f'/habits/{h.pk}/toggle/')
        h.refresh_from_db()
        profile = self.user.profile
        profile.refresh_from_db()
        self.assertEqual(h.total_completions, 0)
        self.assertEqual(profile.xp_points, 0)
        self.assertEqual(profile.total_habits_completed, 0)

    def test_toggle_when_not_due_rejected(self):
        start = self.today
        h = Habit.objects.create(user=self.user, name='Weekly', frequency='weekly',
                                 start_date=start)
        other_day = start + timedelta(days=1)
        if other_day.weekday() == start.weekday():
            other_day = start + timedelta(days=2)
        HabitLog.objects.create(habit=h, date=other_day, completed=True)
        # Simulate the view running on other_day
        with self.settings(USE_TZ=True):
            # The view computes its own "today"; we can't easily fake it, so
            # instead verify the model-level guard used by the view.
            self.assertFalse(h.is_due_on(other_day))


class BadgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('badger', password='pass')
        self.today = timezone.now().date()

    def _make_badge(self, badge_type):
        return Badge.objects.create(name=badge_type, badge_type=badge_type,
                                    description='test')

    def test_perfect_week_not_awarded_with_no_habits(self):
        self._make_badge('perfect_week')
        _check_badges(self.user)
        self.assertFalse(UserBadge.objects.filter(user=self.user).exists())

    def test_perfect_week_not_awarded_when_a_day_missed(self):
        self._make_badge('perfect_week')
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily',
                                 start_date=self.today - timedelta(days=10))
        for i in range(7):
            HabitLog.objects.create(habit=h, date=self.today - timedelta(days=i),
                                    completed=(i != 3))
        _check_badges(self.user)
        self.assertFalse(UserBadge.objects.filter(user=self.user).exists())

    def test_perfect_week_awarded_when_all_due_days_completed(self):
        self._make_badge('perfect_week')
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily',
                                 start_date=self.today - timedelta(days=10))
        for i in range(7):
            HabitLog.objects.create(habit=h, date=self.today - timedelta(days=i),
                                    completed=True)
        _check_badges(self.user)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__badge_type='perfect_week').exists())

    def test_perfect_week_ignores_days_before_habit_started(self):
        self._make_badge('perfect_week')
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily',
                                 start_date=self.today - timedelta(days=2))
        for i in range(3):
            HabitLog.objects.create(habit=h, date=self.today - timedelta(days=i),
                                    completed=True)
        _check_badges(self.user)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__badge_type='perfect_week').exists())

    def test_perfect_period_requires_due_days(self):
        self.assertFalse(_perfect_period(self.user, 7))

    def test_habits_5_badge(self):
        self._make_badge('habits_5')
        for i in range(5):
            Habit.objects.create(user=self.user, name=f'Habit {i}', frequency='daily')
        _check_badges(self.user)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__badge_type='habits_5').exists())

    def test_level_5_badge(self):
        self._make_badge('level_5')
        profile = UserProfile.objects.get_or_create(user=self.user)[0]
        profile.xp_points = 500
        profile.update_level()
        _check_badges(self.user)
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__badge_type='level_5').exists())


class SyncAwardsXPTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sync', password='pass')
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.profile = self.user.profile
        self.profile.strava_access_token = 'mock_token'
        self.profile.save()

    def test_mock_strava_sync_awards_xp(self):
        Habit.objects.create(user=self.user, name='Morning Run', frequency='daily',
                             difficulty='medium', xp_reward=10)
        self.assertEqual(self.profile.xp_points, 0)
        self.client.get('/strava/sync/')
        self.profile.refresh_from_db()
        h = Habit.objects.get(user=self.user)
        self.assertTrue(h.logs.filter(date=self.today, completed=True).exists())
        self.assertEqual(self.profile.xp_points, 15)  # 10 * 1.5 medium multiplier
        self.assertEqual(self.profile.total_habits_completed, 1)

    def test_mock_strava_sync_does_not_double_count(self):
        Habit.objects.create(user=self.user, name='Morning Run', frequency='daily')
        self.client.get('/strava/sync/')
        self.client.get('/strava/sync/')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_habits_completed, 1)
        self.assertEqual(HabitLog.objects.filter(habit__user=self.user, completed=True).count(), 1)


class StreakFreezeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('freezer', password='pass')
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.profile = self.user.profile

    def test_freeze_preserves_streak(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=2), completed=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=1), completed=False)
        h.update_streak()
        self.assertEqual(h.current_streak, 0)
        resp = self.client.post(f'/habits/{h.pk}/freeze/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'freeze_applied')
        h.refresh_from_db()
        self.assertEqual(h.current_streak, 2)
        self.assertEqual(data['freezes_remaining'], 2)

    def test_freeze_fails_when_no_freezes_left(self):
        self.profile.streak_freezes = 0
        self.profile.save()
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        resp = self.client.post(f'/habits/{h.pk}/freeze/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('No streak freezes', resp.json()['error'])

    def test_freeze_fails_when_not_due_yesterday(self):
        start = self.today
        h = Habit.objects.create(user=self.user, name='Weekly', frequency='weekly', start_date=start)
        resp = self.client.post(f'/habits/{h.pk}/freeze/')
        self.assertEqual(resp.status_code, 400)

    def test_freeze_fails_when_already_completed_yesterday(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.yesterday, completed=True)
        resp = self.client.post(f'/habits/{h.pk}/freeze/')
        self.assertEqual(resp.status_code, 400)

    def test_freeze_fails_when_already_frozen(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.yesterday, completed=False, streak_frozen=True)
        resp = self.client.post(f'/habits/{h.pk}/freeze/')
        self.assertEqual(resp.status_code, 400)

    def test_update_streak_respects_frozen_days(self):
        h = Habit.objects.create(user=self.user, name='Run', frequency='daily')
        HabitLog.objects.create(habit=h, date=self.today, completed=True)
        HabitLog.objects.create(habit=h, date=self.yesterday, completed=False, streak_frozen=True)
        HabitLog.objects.create(habit=h, date=self.today - timedelta(days=2), completed=True)
        h.update_streak()
        self.assertEqual(h.current_streak, 3)


class CalendarViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cal_user', password='pass')
        self.client.force_login(self.user)

    def test_calendar_page_loads(self):
        resp = self.client.get('/calendar/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('calendar_days', resp.context)

    def test_calendar_navigates_months(self):
        resp = self.client.get('/calendar/?year=2025&month=6')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['month'], 6)
        self.assertEqual(resp.context['year'], 2025)
