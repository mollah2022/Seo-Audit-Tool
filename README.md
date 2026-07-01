# SEO Audit Tool

A Django (MVT architecture) web app that audits a website's on-page SEO,
technical SEO, and performance. Frontend is rendered with Django Templates —
no separate frontend framework.

## Tech stack

- **Backend / Frontend:** Django (MVT), Django Templates
- **Crawler (next step):** Playwright
- **Database:** SQLite (local dev)

## Project structure

```
seo_audit_tool/
├── config/             # Project settings, root urls.py, wsgi/asgi
├── audits/             # Main app: models, views, urls, services/
│   └── services/        # Crawler + SEO check logic (added next)
├── templates/           # Django templates (base.html, partials/, audits/)
├── static/               # CSS / JS / images
├── media/                # Screenshots, exports (gitignored, dir kept)
├── manage.py
├── requirements.txt
└── .env.example
```

## Local setup

1. **Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` if needed (default values work fine for local development).

4. **Run migrations**

   ```bash
   python manage.py migrate
   ```

5. **Run the development server**

   ```bash
   python manage.py runserver
   ```

6. Visit **http://127.0.0.1:8000/** — you should see the homepage with the
   "Run Audit" form.

## What's built so far

- Project scaffolding (`config/`, `audits/` app)
- Base template + navbar/footer partials
- Static file setup (CSS/JS)
- Homepage with a URL input form (not yet wired to a real audit)

## What's next

- Add `Audit` and `CheckResult` models
- Build `audits/services/crawler.py` using Playwright
- Build on-page, technical, and performance checkers
- Wire the form on the homepage to a "run audit" view + results page
