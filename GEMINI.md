# RecomenRestaurant (SmartResto) - Developer Guide

## Project Overview
**RecomenRestaurant** (SmartResto) is a Flask-based restaurant discovery, management, and market platform in Trujillo, Peru. It connects diners with local eateries, schedule-based shopping, recipe stock tracking, and order workflows.

- **Backend & Web Framework:** Python Flask (`Flask==3.0.0`, Flask-Login, Flask-WTF, Werkzeug).
- **Database & Storage:** Supabase PostgreSQL (`psycopg[binary]`). All core models store JSONB documents in `public.app_records`. Administrative AI decisions are logged in `public.ai_decisions`.
- **AI Integrations:** 
  - Groq / Qwen (`QWEN_API_KEY`, `QWEN_MODEL`, `ADMIN_QWEN_MODEL`) for discovery, chat, and text extraction.
  - Google Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`) for photo/menu document reading and auditing.
- **Geospatial & Analysis:** `geopy`, `haversine`, `pandas`, `openpyxl`, `python-docx`.
- **Testing:** `pytest` with a dedicated PostgreSQL test database.

---

## Setup and Running

### Environment Setup (Python 3.12 on Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m scripts.secret_key
```

### Configuration
1. Update `.env` with the generated `SECRET_KEY`.
2. Configure `DATABASE_URL` with your Supabase PostgreSQL connection string (`DATABASE_SSLMODE=require`).
3. Execute SQL setup scripts in Supabase:
   - `database/app_records.sql`
   - `database/ai_decisions.sql`
4. Create an administrator account:
   ```powershell
   python -m scripts.create_user
   ```

### Running the Application
```powershell
python app.py
```
Access the application at `http://127.0.0.1:5000`.

---

## Testing & Quality Assurance
Run the test suite using `pytest`:

```powershell
$env:DATABASE_URL = '<TEST_DATABASE_URL>'
$env:SMARTRESTO_TEST_DATABASE_URL = $env:DATABASE_URL
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$env:FLASK_DEBUG = '0'
python -m pytest -q test
```

---

## Development Conventions & Architecture
- **CSRF Protection:** All POST forms require a `csrf_token`. JSON clients must include the page token in the `X-CSRFToken` header.
- **Authentication & Roles:** Managed via Flask-Login supporting Diner (*Comensal*), Business Owner (*Empresario*), and Administrator (*Administrador*) roles. Use `python -m scripts.test_auth` to verify credentials.
- **Data Persistence:** Models interact with PostgreSQL JSONB storage via repository patterns (`database/repository.py`).
- **Code Style:** Adhere strictly to PEP 8, maintain type safety, and write comprehensive pytest test cases for new features or bug fixes.
