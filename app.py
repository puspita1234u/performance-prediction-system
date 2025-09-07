import os
import pandas as pd
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

MODEL = None
# Update feature list to match your actual schema
FEATURE_COLUMNS = [
    "age",
    "previous_marks",
    "attendance_percent",
    "study_hours_per_week",
    "family_income",
    "assignment_score",
    "gender",
    "parental_education",
    "internet_access",
    "extra_classes"
]

MODEL_PATH = os.path.join("models", "student_model.joblib")

try:
    if os.path.exists(MODEL_PATH):
        MODEL = joblib_load(MODEL_PATH)
        print(f"ML model loaded successfully from {MODEL_PATH}")
    else:
        print(f"ML model not found at {MODEL_PATH}. Using fallback prediction.")
except Exception as e:
    MODEL = None
    print(f"Failed to load ML model: {e}")

# ---------------- Models ----------------
class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    __tablename__ = 'student_record'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
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

    teacher = db.relationship('Teacher', backref=db.backref('students', lazy=True))

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

def predict_student_performance(student):
    """
    Predict performance for a single student using the trained ML model.
    Falls back gracefully if model is missing or fields are incomplete.
    """
    if MODEL is None:
        print("MODEL is not loaded. Using fallback prediction.")
        return "Fail", 0.0

    # Build feature dictionary in the exact order as training
    sample = {
        "age": student.age,
        "previous_marks": student.previous_marks,
        "attendance_percent": student.attendance_percent,
        "study_hours_per_week": student.study_hours_per_week,
        "family_income": student.family_income,
        "assignment_score": student.assignment_score,
        "gender": student.gender,
        "parental_education": student.parental_education,
        "internet_access": student.internet_access,
        "extra_classes": student.extra_classes,
    }

    try:
        df = pd.DataFrame([sample], columns=FEATURE_COLUMNS)
        y_pred = MODEL.predict(df)[0]
        prob = MODEL.predict_proba(df)[0].max()
        label = "Pass" if int(y_pred) == 1 else "Fail"
        return label, float(prob)
    except Exception as e:
        print(f"Prediction failed for student {student.id}: {e}")
        return "Fail", 0.0

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

    chart_labels = [s.name for s in students]
    chart_marks = [s.previous_marks or 0 for s in students]

    # Compute summary
    total = len(students)
    passes = sum(1 for s in students if s.prediction == "Pass")
    fails = sum(1 for s in students if s.prediction == "Fail")
    avg_prob_pass = round(sum(s.probability for s in students if s.prediction == "Pass") / passes, 2) if passes else 0
    avg_prob_fail = round(sum(s.probability for s in students if s.prediction == "Fail") / fails, 2) if fails else 0

    return render_template(
        "dashboard.html",
        students=students,
        chart_labels=chart_labels,
        chart_marks=chart_marks,
        total=total,
        passes=passes,
        fails=fails,
        avg_prob_pass=avg_prob_pass,
        avg_prob_fail=avg_prob_fail
    )

@app.route("/students/add_student", methods=["POST"])
def add_student():
    # Ensure teacher is logged in
    teacher_check = require_teacher()
    if teacher_check:
        return teacher_check

    tid = current_teacher_id()
    if not tid:
        flash("Unable to determine teacher. Please log in again.", "danger")
        return redirect(url_for("login"))

    # Extract form fields
    name = request.form.get("name", "").strip()
    age = request.form.get("age") or None
    assignment_score = request.form.get("assignment_score") or None
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

    # Create new student linked to teacher
    s = Student(
        teacher_id=tid,  # <-- Link the student to the teacher
        name=name,
        age=int(age) if age else None,
        assignment_score=float(assignment_score) if assignment_score else None,
        gender=gender,
        previous_marks=int(previous_marks) if previous_marks else None,
        attendance_percent=int(attendance_percent) if attendance_percent else (
            int(attendance) if attendance else None
        ),
        study_hours_per_week=int(study_hours_per_week) if study_hours_per_week else None,
        parental_education=parental_education,
        family_income=int(family_income) if family_income else None,
        internet_access=internet_access,
        extra_classes=extra_classes
    )

    db.session.add(s)
    db.session.commit()
    flash("Student added successfully.", "success")
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
        s.assignment_score = float(request.form.get("assignment_score") or 0) or None
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
def predict_student(student_id):
    if "teacher_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    s = Student.query.get_or_404(student_id)
    if s.teacher_id != session["teacher_id"]:
        return jsonify({"error": "Forbidden"}), 403

    label, prob = predict_student_performance(s)
    s.prediction = label
    s.probability = prob
    db.session.commit()

    return jsonify({
        "id": s.id,
        "prediction": label,
        "probability": prob
    })


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

@app.route("/students/predict_all", methods=["POST"])
def predict_all():
    if "teacher_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    tid = session["teacher_id"]
    print(f"PredictAll triggered for teacher_id: {tid}")

    students = Student.query.filter_by(teacher_id=tid).all()
    print(f"Found {len(students)} students for prediction")

    if not students:
        return jsonify({"updated": 0, "students": []})

    updated_students = []
    count = 0

    for s in students:
        label, prob = predict_student_performance(s)
        s.prediction = label
        s.probability = prob
        updated_students.append({
            "id": s.id,
            "prediction": label,
            "probability": round(prob * 100, 1)
        })
        count += 1

    db.session.commit()
    return jsonify({"updated": count, "students": updated_students})

@app.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    if require_teacher():
        return require_teacher()

    s = Student.query.get_or_404(student_id)

    # Ensure logged-in teacher owns the student
    if s.teacher_id != current_teacher_id():
        flash("Not authorized to delete this student.", "danger")
        return redirect(url_for("dashboard"))

    db.session.delete(s)
    db.session.commit()
    flash("Student deleted successfully.", "info")
    return redirect(url_for("dashboard"))



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
