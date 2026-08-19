from django.contrib import admin
from .models import Habit, HabitLog, Category, UserProfile, Badge, UserBadge


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'xp_points', 'total_habits_completed', 'longest_streak']
    search_fields = ['user__username', 'user__email']
    list_filter = ['level']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color', 'icon']
    list_filter = ['user']
    search_fields = ['name', 'user__username']


class HabitLogInline(admin.TabularInline):
    model = HabitLog
    extra = 0
    fields = ['date', 'completed', 'note', 'mood']
    readonly_fields = ['date']


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'category', 'frequency', 'priority', 'current_streak', 'total_completions', 'is_active']
    list_filter = ['frequency', 'priority', 'difficulty', 'is_active', 'is_archived']
    search_fields = ['name', 'user__username']
    inlines = [HabitLogInline]
    readonly_fields = ['current_streak', 'best_streak', 'total_completions', 'created_at']


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ['habit', 'date', 'completed', 'mood', 'completed_at']
    list_filter = ['completed', 'mood', 'date']
    search_fields = ['habit__name', 'habit__user__username']
    date_hierarchy = 'date'


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge_type', 'description']


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge']
    search_fields = ['user__username', 'badge__name']


admin.site.site_header = "GoalAchiever Admin"
admin.site.site_title = "GoalAchiever"
admin.site.index_title = "Habit Tracker Management"
