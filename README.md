# Student Performance Portal

Flask + MySQL web app for managing students by **Teachers**, predicting pass/fail, and an **Admin** panel to view teachers & their students.

## Features
- Teacher **Signup/Login/Logout**.
- Teacher dashboard to **add/edit students**, **predict** pass/fail with percentage.
- Student table with **Predict** button per row; result filled in `prediction` column.
- Click **Student ID** hyperlink to edit details.
- **Admin** login to view all teachers; click a teacher to view their students.
- Optional ML model integration via `models/student_model.joblib` (falls back to rule-based score if missing).
- Simple chart on dashboard (marks per student) using Chart.js.

## Tech
- Python (Flask, SQLAlchemy)
- MySQL (via `pymysql`). You can switch to SQLite quickly for testing.
- Bootstrap 5 + Chart.js

## Setup

1. **Clone & install**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate

pip install -r requirements.txt
```

2. **Configure environment**
- Copy `.env.example` to `.env` and update values (SECRET_KEY, DATABASE_URL).
- Example MySQL URL:
```
DATABASE_URL=mysql+pymysql://<db_user>:<db_pass>@localhost:3306/studentsdb
```

3. **Create DB tables**
```bash
# Option A: via Flask CLI
python app.py  # first run auto-creates tables
# OR explicitly:
flask --app app.py init-db
```

4. **Create Admin**
```bash
flask --app app.py create-admin
# uses ADMIN_USERNAME and ADMIN_PASSWORD from .env (defaults: admin / admin123)
```

5. **Run**
```bash
python app.py
# open http://localhost:5000
```

6. **(Optional) Add ML model**
- Save your scikit-learn model to `models/student_model.joblib`.
- Expected features (order): `marks`, `attendance`, `assignment_score`.
- If `predict_proba` exists, the positive class probability is used (x100). If not, regression output is clamped to 0..100.

## Notes
- For production, change SECRET_KEY and disable debug.
- Ensure your MySQL server is running and `studentsdb` database exists.
- To quickly test without MySQL, set `DATABASE_URL=sqlite:///students.db` in `.env`.
