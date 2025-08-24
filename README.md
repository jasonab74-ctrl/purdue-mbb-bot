# Purdue MBB News/Chat Bot (UI at /ui)

Continuously collects Purdue men's basketball stories from NCAA, Hammer & Rails, PurdueSports.com, and Reddit.

### Features
- Refreshes every few minutes (via worker/cron).
- Stores articles in SQLite with full-text search.
- Exposes a FastAPI backend:
  - `/healthz`
  - `/latest`
  - `/search?q=...`
  - `/chat?question=...`
- Simple built-in web UI at `/ui`.

### Deployment
- Built for [Render](https://render.com) using `render.yaml`.
- Web service runs the API.
- Worker service runs the collectors (RSS, Purdue pages, Reddit).
- Requires Reddit API credentials (`.env.example` shows what you need).

### Next Steps
- Add more RSS feeds (On3, 247, Gold & Black) in `app/collect.py`.
- Optional: add push notifications (Discord/Telegram).
