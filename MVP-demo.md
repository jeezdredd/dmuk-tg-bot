# 🎓 UniBot - University Assistant

## Overview
Telegram bot aggregating university news, schedules, and services in one place.

## Core Features

### Phase 1: MVP
- **News Aggregator** - Parse from Telegram channels, categorize, notify
- **Schedule System** - Class schedules, changes, calendar export
- **User Profiles** - Registration, preferences, subscriptions

### Phase 2: Academic
- **Exam Calendar** - Dates, deadlines, reminders
- **Campus Navigation** - Maps, classroom finder, contacts
- **Smart Notifications** - Priority alerts, customizable

### Phase 3: Advanced
- **AI Assistant** - FAQ, natural language queries
- **Student Community** - Study groups, file sharing
- **Services** - Room booking, document requests

### Phase 4: Integration
- **University Systems** - Student portal, grades, payments
- **Multi-platform** - Web app, mobile
- **ML Features** - Personalized recommendations

## Architecture

```
Students → Telegram Bot → API Server → Database
                              ↓
                         Background Workers
                              ↓
                      Telegram Channels
                      University Systems
```

## Tech Stack
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, Redis
- **Queue:** RabbitMQ, Celery
- **Bot:** aiogram
- **Parser:** Telethon
- **Deploy:** Docker

## Benefits
- **Students:** All info in one place, never miss updates
- **University:** Better communication, reduced staff workload
- **Faculty:** Direct channel to students

## Metrics
- 50%+ student adoption
- 99.5% uptime
- <200ms response time
- 70%+ weekly active users

## Timeline
- **Phase 1:** 2-3 months
- **Phase 2:** 3-4 months
- **Phase 3:** 4-5 months
- **Phase 4:** 4-6 months

**Total:** 12-18 months