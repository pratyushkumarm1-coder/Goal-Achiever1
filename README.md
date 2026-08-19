# GoalAchiever — Habit Tracker

**Track habits. Build streaks. Achieve goals.**

A full-stack Django habit tracker with gamification, integrations, and modern glassmorphism UI.

## Features

- **Habit Management** — Create daily, weekly, weekday, or weekend habits with priorities, difficulty levels, and custom colors/icons
- **Streak System** — Automatic streak tracking with streak freezes (3 tokens) to protect progress on missed days
- **XP & Leveling** — Earn XP based on habit difficulty (Easy 1x, Medium 1.5x, Hard 2x), level up from Beginner to Elite
- **Badges & Achievements** — 13 badge types including 7/30/100-day streaks, perfect week/month, early bird, night owl
- **Calendar View** — Month grid with color-coded days (green=perfect, blue=frozen, yellow=partial, red=missed)
- **Analytics Dashboard** — 30-day charts, per-habit completion rates, category distribution, best performing habits
- **Reminder Alarms** — Set reminder times per habit with Web Audio chime + browser notifications via Service Worker (works in background)
- **Strava Integration** — Connect/mock sync to auto-complete fitness habits from activities
- **Spotify Integration** — Search, play, and embed music; auto-complete music habits from listening history
- **Password Reset** — Full email-based reset flow with console email backend for local dev
- **Dark/Light Theme** — Toggle between themes with persistent preference
- **Offline Support** — Service Worker caches static assets, PWA manifest for phone installation

## Tech Stack

- **Backend:** Django 4.x, SQLite
- **Frontend:** Bootstrap 5.3, Chart.js, Bootstrap Icons, Custom glassmorphism CSS
- **Auth:** Django built-in with custom forms
- **Integrations:** Strava OAuth, Spotify OAuth + Web Playback SDK
- **PWA:** Service Worker, Web App Manifest

## Quick Start

```bash
pip install django pillow python-dotenv requests
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` — register a new account or use `demo` / `demo12345`.

## Tests

```bash
python manage.py test tracker
```

28 tests covering frequency logic, streaks, XP, badges, freeze, calendar, and sync.

## Project Structure

```
Goal Achiever/
├── habit_tracker/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tracker/                # Main app
│   ├── models.py           # Habit, HabitLog, UserProfile, Badge, Category
│   ├── views.py            # All views + API endpoints
│   ├── urls.py             # URL routing
│   ├── forms.py            # Custom forms
│   ├── tests.py            # 28 tests
│   ├── signals.py          # Auto-create UserProfile
│   └── admin.py            # Admin registration
├── templates/tracker/      # All templates
│   ├── base.html           # Layout + sidebar + service worker
│   ├── dashboard.html      # Main dashboard with alarms, charts, habits
│   ├── calendar.html       # Month calendar view
│   ├── analytics.html      # Analytics with 3 charts
│   ├── profile.html        # Profile + badges + integrations
│   ├── habit_form.html     # Create/edit habit
│   ├── habit_detail.html   # Single habit view
│   ├── habit_list.html     # All habits list
│   ├── password_reset*.html # 4 password reset templates
│   └── ...
├── static/
│   ├── css/style.css       # Full glassmorphism theme
│   ├── js/main.js          # Sidebar, theme, toggle habit
│   ├── js/sw.js            # Service Worker (offline + notifications)
│   ├── js/spotify_player.js # Spotify search/play SDK
│   └── manifest.json       # PWA manifest
└── manage.py
```

## Screenshots

| Dashboard | Calendar | Analytics |
|-----------|----------|-----------|
| Progress ring, habit cards, heatmap, Spotify player | Color-coded month grid with streak freeze indicators | 30-day trends, per-habit rates, category breakdown |

## License

MIT
