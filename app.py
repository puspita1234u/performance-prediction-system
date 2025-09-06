import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from joblib import load as joblib_load

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_change_me")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///students.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- Models ----------------
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    marks = db.Column(db.Float)
    attendance = db.Column(db.Float)
    assignment_score = db.Column(db.Float)
    prediction = db.Column(db.String(50))

    gender = db.Column(db.String(1))
    previous_marks = db.Column(db.Integer)
    attendance_percent = db.Column(db.Integer)
    study_hours_per_week = db.Column(db.Integer)
    parental_education = db.Column(db.String(32))
    family_income = db.Column(db.Integer)
    internet_access = db.Column(db.String(3))
    extra_classes = db.Column(db.String(3))
    probability = db.Column(db.Float)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# ---------------- Utilities ----------------
def current_teacher_id():
    return session.get("teacher_id")

def require_teacher():
    if not current_teacher_id():
        return redirect(url_for("login"))
    return None

def is_admin():
    return session.get("admin", False)

# Try to load ML model (optional). If missing, fallback to a simple rule.
MODEL = None
MODEL_FEATURES = ["marks", "attendance", "assignment_score"]
try:
    MODEL = joblib_load(os.path.join("models", "student_model.joblib"))
except Exception:
    MODEL = None

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("index.html")

# --------- Teacher Auth ---------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("signup"))
        if Teacher.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("signup"))
        hashed = generate_password_hash(password)
        t = Teacher(name=name, email=email, password=hashed)
        db.session.add(t)
        db.session.commit()
        flash("Signup successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        teacher = Teacher.query.filter_by(email=email).first()
        if teacher and check_password_hash(teacher.password, password):
            session.clear()
            session["teacher_id"] = teacher.id
            session["teacher_name"] = teacher.name
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))

# --------- Teacher Dashboard & Students ---------
@app.route("/dashboard")
def dashboard():
    if require_teacher():
        return require_teacher()
    tid = current_teacher_id()
    students = Student.query.filter_by(teacher_id=tid).order_by(Student.id.desc()).all()
    # Provide data for chart
    chart_labels = [s.name for s in students]
    chart_marks = [s.marks or 0 for s in students]
    return render_template("dashboard.html", students=students, chart_labels=chart_labels, chart_marks=chart_marks)

@app.route("/students/add", methods=["POST"])
def add_student():
    if require_teacher():
        return require_teacher()
    tid = current_teacher_id()
    name = request.form.get("name","").strip()
    age = request.form.get("age") or None
    marks = request.form.get("marks") or None
    attendance = request.form.get("attendance") or None
    assignment_score = request.form.get("assignment_score") or None

    # new fields
    gender = request.form.get("gender") or None
    previous_marks = request.form.get("previous_marks") or None
    attendance_percent = request.form.get("attendance_percent") or None
    study_hours_per_week = request.form.get("study_hours_per_week") or None
    parental_education = request.form.get("parental_education") or None
    family_income = request.form.get("family_income") or None
    internet_access = request.form.get("internet_access") or None
    extra_classes = request.form.get("extra_classes") or None

    if not name:
        flash("Student name is required.", "danger")
        return redirect(url_for("dashboard"))
    s = Student(
        teacher_id=tid,
        name=name,
        age=int(age) if age else None,
        marks=float(marks) if marks else None,
        attendance=float(attendance) if attendance else None,
        assignment_score=float(assignment_score) if assignment_score else None,
        gender=gender,
        previous_marks=int(previous_marks) if previous_marks else None,
        attendance_percent=int(attendance_percent) if attendance_percent else (int(attendance) if attendance else None),
        study_hours_per_week=int(study_hours_per_week) if study_hours_per_week else None,
        parental_education=parental_education,
        family_income=int(family_income) if family_income else None,
        internet_access=internet_access,
        extra_classes=extra_classes
    )
    db.session.add(s)
    db.session.commit()
    flash("Student added.", "success")
    return redirect(url_for("dashboard"))

@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    if require_teacher():
        return require_teacher()
    s = Student.query.get_or_404(student_id)
    # Ensure the student belongs to the logged-in teacher
    if s.teacher_id != current_teacher_id():
        flash("Not authorized to edit this student.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        s.age = int(request.form.get("age") or 0) or None
        s.marks = float(request.form.get("marks") or 0) or None
        s.attendance = float(request.form.get("attendance") or 0) or None
        s.assignment_score = float(request.form.get("assignment_score") or 0) or None

        # new fields
        s.gender = request.form.get("gender") or s.gender
        s.previous_marks = int(request.form.get("previous_marks") or 0) or s.previous_marks
        s.attendance_percent = int(request.form.get("attendance_percent") or 0) or s.attendance_percent
        s.study_hours_per_week = int(request.form.get("study_hours_per_week") or 0) or s.study_hours_per_week
        s.parental_education = request.form.get("parental_education") or s.parental_education
        s.family_income = int(request.form.get("family_income") or 0) or s.family_income
        s.internet_access = request.form.get("internet_access") or s.internet_access
        s.extra_classes = request.form.get("extra_classes") or s.extra_classes

        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_student.html", student=s)

# Example predict route — adapt to your actual route name/path
@app.route("/students/<int:student_id>/predict", methods=["POST"])
def predict(student_id):
    if "teacher_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    s = Student.query.get_or_404(student_id)
    if s.teacher_id != session["teacher_id"]:
        return jsonify({"error": "Forbidden"}), 403

    # Build features (adjust to your model)
    sample = {
        "gender": (s.gender or "F"),
        "age": int(s.age or 0),
        "previous_marks": int(s.previous_marks or s.marks or 0),
        "attendance_percent": int(s.attendance_percent or s.attendance or 0),
        "study_hours_per_week": int(s.study_hours_per_week or 0),
        "parental_education": (s.parental_education or "HighSchool"),
        "family_income": int(s.family_income or 0),
        "internet_access": (s.internet_access or "Yes"),
        "extra_classes": (s.extra_classes or "No"),
        "assignment_score": int(s.assignment_score or 0),
    }

    label = "Fail"
    prob = 0.0
    try:
        import pandas as pd
        df = pd.DataFrame([sample])
        pred = MODEL.predict(df)[0]
        label = "Pass" if int(pred) == 1 else "Fail"
        if hasattr(MODEL, "predict_proba"):
            prob = float(MODEL.predict_proba(df)[:, 1][0])  # 0..1
    except Exception:
        # simple heuristic fallback
        score = sample["previous_marks"]*0.6 + sample["attendance_percent"]*0.3 + sample["study_hours_per_week"]*0.1
        prob = min(1.0, max(0.0, score/100.0))
        label = "Pass" if prob >= 0.5 else "Fail"

    s.prediction = label              # <-- plain Pass/Fail
    s.probability = float(prob)       # <-- 0..1
    db.session.commit()

    return jsonify({"prediction": s.prediction, "probability": s.probability})


# --------- Admin ---------
@app.route("/admin", methods=["GET", "POST"]
)
def admin_login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session.clear()
            session["admin"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Admin logged out.", "info")
    return redirect(url_for("home"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))
    teachers = Teacher.query.order_by(Teacher.id.desc()).all()
    return render_template("admin_dashboard.html", teachers=teachers)

@app.route("/admin/teachers/<int:teacher_id>")
def admin_view_students(teacher_id):
    if not is_admin():
        return redirect(url_for("admin_login"))
    teacher = Teacher.query.get_or_404(teacher_id)
    students = Student.query.filter_by(teacher_id=teacher_id).order_by(Student.id.desc()).all()
    return render_template("view_students.html", teacher=teacher, students=students)

@app.route("/api/stats")
def api_stats():
    from sqlalchemy import func

    if "teacher_id" in session:
        tid = session["teacher_id"]
        total = Student.query.filter_by(teacher_id=tid).count()
        passes = Student.query.filter_by(teacher_id=tid, prediction="Pass").count()
        fails = Student.query.filter_by(teacher_id=tid, prediction="Fail").count()
        avg_prob_pass = db.session.query(func.avg(Student.probability)).filter_by(teacher_id=tid, prediction="Pass").scalar() or 0
        avg_prob_fail = db.session.query(func.avg(Student.probability)).filter_by(teacher_id=tid, prediction="Fail").scalar() or 0

        return jsonify({
            "total": total,
            "passes": passes,
            "fails": fails,
            "avg_prob_pass": float(avg_prob_pass),
            "avg_prob_fail": float(avg_prob_fail)
        })

    return jsonify({"total": 0, "passes": 0, "fails": 0, "avg_prob_pass": 0, "avg_prob_fail": 0})


# --------- CLI helpers ---------

@app.cli.command("init-db")
def init_db():
    """Initialize database tables."""
    db.create_all()
    print("Database initialized.")

@app.cli.command("create-admin")
def create_admin():
    """Create admin user from .env credentials (ADMIN_USERNAME / ADMIN_PASSWORD)."""
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    if Admin.query.filter_by(username=username).first():
        print("Admin already exists.")
        return
    hashed = generate_password_hash(password)
    a = Admin(username=username, password=hashed)
    db.session.add(a)
    db.session.commit()
    print(f"Admin '{username}' created.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
