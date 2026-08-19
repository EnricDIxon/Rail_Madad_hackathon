RailMadad — Backend API (Prototype)
===================================

Brief
-----
This repository contains the Flask backend for the RailMadad prototype: an API to receive passenger complaints (JSON or multipart with image), run light AI analysis (Gemini or local heuristic), group similar reports, and serve uploads.

Quick start (development)
-------------------------
1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r API/requirements.txt
```

2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` if you want AI integration:

```powershell
Copy-Item .env.example .env
# edit .env and set GEMINI_API_KEY
```

3. Run the server (development):

```powershell
.\.venv\Scripts\python API\app.py
```

Core endpoints
--------------
- `POST /api/complaints` — Accepts JSON or `multipart/form-data` with an optional `image` field. Returns the saved complaint.
- `GET /api/complaints` — List complaints with filters and pagination. Query params: `status`, `department`, `train_number`, `coach`, `search`, `from`, `to`, `limit`, `offset`.
- `GET /api/complaints/<id>` — Get a single complaint.
- `PATCH /api/complaints/<id>` — Update allowed fields (`status`, `department`, `category`, `subcategory`, `severity`, `summary`).
- `GET /api/complaints/recurring` — Returns grouped summaries by `group_key` with counts.
- `GET /uploads/<filename>` — Serve uploaded files (prototype only).

Data & files
-----------
- Database: `Database/complaints.db` (SQLite) — ignored by git.
- Uploads: `uploads/` folder; image paths stored as `uploads/<filename>` and served from `/uploads/`.

Notes for frontend integration
-----------------------------
- CORS is enabled. Frontend can POST `multipart/form-data` for uploads. Use returned `image_path` to display images.
- Use `limit`/`offset` and filters on `GET /api/complaints` to build paged lists. Use `GET /api/complaints/recurring` to show grouped issues.

Testing & development
---------------------
- `API/api_smoke.py` was a small internal smoke tester (removed in cleanup). Use Postman or the sample scripts to exercise endpoints.

Next steps (suggested)
----------------------
- Add CSV export for admin and/or store full raw AI response for auditing if needed.
- Add OpenAPI spec and a minimal frontend to demo the flow.

License & Security
------------------
- Do not commit `.env` or the SQLite DB. The repo `.gitignore` already excludes them.

Contact
-------
For integration questions ask the backend developer.
# RailMadad

Project placeholder README. Initial commit to create a tracked file for pushing to GitHub.
