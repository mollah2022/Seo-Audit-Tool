# SEO Audit Tool

SEO Audit Tool is a Django web application that scans websites for SEO issues and displays a saved audit report with score, summary, and category results. The app uses Django templates for rendering and a set of service modules to analyze on-page, technical, social, link, and performance signals.

## Features

- Submit a website URL for a new SEO scan
- View a detailed report with category-based results
- Save audit history for later viewing
- Open a saved report from history
- Delete a saved audit from history
- Download a saved report as a PDF

## Tech stack

- Backend: Django 6.0
- Frontend: Django Templates, HTML, CSS, JavaScript
- Database: SQLite
- Browser automation: Playwright
- Parsing: BeautifulSoup
- HTTP requests: Requests

## Project structure

```text
seo_audit_tool/
├── audits/                  # Main Django app
│   ├── management/          # Custom Django management commands
│   ├── migrations/          # Database migrations
│   ├── services/            # SEO audit logic and checks
│   ├── templates/           # App templates (if any)
│   ├── models.py            # Audit and CheckResult models
│   ├── views.py             # Homepage, history, detail, delete, PDF views
│   └── urls.py              # App routes
├── config/                  # Django settings and URL configuration
├── static/                  # CSS, JS, images
├── templates/               # Base templates and shared UI partials
├── media/                   # Media output such as screenshots or exports
├── manage.py                # Django entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables
└── db.sqlite3               # Local development database
```

## Prerequisites

Make sure you have the following installed on your machine:

- Python 3.10+ recommended
- pip
- Git

## Clone the repository

```bash
git clone https://github.com/mollah2022/Seo-Audit-Tool.git
cd Seo-Audit-Tool
```

## Setup instructions

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If you are on Windows PowerShell, use:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3) Create environment variables

```bash
cp .env.example .env
```

Open `.env` and update the values if needed. The default settings are usually fine for local development.

### 4) Apply database migrations

```bash
python manage.py migrate
```

### 5) Start the server

```bash
python manage.py runserver
```

Then open the application in your browser:

```text
http://127.0.0.1:8000/
```

## How to use the app

1. Open the homepage.
2. Enter a website URL in the scan form.
3. Submit the form to start the audit.
4. View the SEO report once the scan completes.
5. Visit the History page to see saved audits, open reports, delete records, or download PDFs.

## Running tests

```bash
python manage.py test audits.tests
```

## Notes

- The project uses SQLite for local development, so no external database setup is required.
- Playwright may need its browser binaries installed on first use. If the crawler reports a browser issue, install Playwright browsers with:

```bash
python -m playwright install
```

## License

This project is open source. Please check the repository license before using it in production.
