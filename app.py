from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db
from risk import compute_risk, recompute_one

app = Flask(__name__)
app.secret_key = "change-this-later"  # signs the login cookie


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        matric_no = request.form["matric_no"].strip()
        department = request.form["department"].strip()

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return render_template("signup.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role, matric_no, department) "
                "VALUES (?,?,?,?,?,?)",
                (name, email, generate_password_hash(password), "student", matric_no, department),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered.")
            return render_template("signup.html")
        finally:
            conn.close()

        flash("Account created. Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if session["role"] == "lecturer":
        courses = conn.execute(
            """
            SELECT c.id, c.code, c.title,
                   COUNT(e.id) AS students,
                   COALESCE(SUM(CASE WHEN r.level = 'high' THEN 1 ELSE 0 END), 0) AS high,
                   COALESCE(SUM(CASE WHEN r.level = 'moderate' THEN 1 ELSE 0 END), 0) AS moderate
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN risk_assessments r ON r.enrollment_id = e.id
            WHERE c.lecturer_id = ?
            GROUP BY c.id
            """,
            (session["user_id"],),
        ).fetchall()
        conn.close()
        return render_template(
            "dashboard.html",
            courses=courses,
            total_students=sum(c["students"] for c in courses),
            total_high=sum(c["high"] for c in courses),
            total_moderate=sum(c["moderate"] for c in courses),
        )

    my_courses = conn.execute(
        """
        SELECT e.id AS enrollment_id, c.code, c.title, r.risk_score, r.level
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        LEFT JOIN risk_assessments r ON r.enrollment_id = e.id
        WHERE e.student_id = ?
        ORDER BY r.risk_score DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", my_courses=my_courses)

@app.route("/course/<int:course_id>")
def course(course_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "lecturer":
        return redirect(url_for("dashboard"))

    conn = get_db()
    # Only the lecturer who teaches this course may open it
    c = conn.execute(
        "SELECT * FROM courses WHERE id = ? AND lecturer_id = ?",
        (course_id, session["user_id"]),
    ).fetchone()
    if c is None:
        conn.close()
        abort(404)

    students = conn.execute(
        """
        SELECT e.id AS enrollment_id, u.name, u.matric_no, r.risk_score, r.level
        FROM enrollments e
        JOIN users u ON u.id = e.student_id
        LEFT JOIN risk_assessments r ON r.enrollment_id = e.id
        WHERE e.course_id = ?
        ORDER BY r.risk_score DESC
        """,
        (course_id,),
    ).fetchall()
    conn.close()
    return render_template("course.html", course=c, students=students)

@app.route("/enrollment/<int:enrollment_id>")
def enrollment(enrollment_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "lecturer":
        return redirect(url_for("dashboard"))

    conn = get_db()
    # Only the lecturer who teaches the course may see this student's record
    e = conn.execute(
        """
        SELECT e.id, u.name, u.matric_no, c.id AS course_id, c.code, c.title
        FROM enrollments e
        JOIN users u ON u.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        WHERE e.id = ? AND c.lecturer_id = ?
        """,
        (enrollment_id, session["user_id"]),
    ).fetchone()
    if e is None:
        conn.close()
        abort(404)

    rows = conn.execute(
        "SELECT kind, label, score, max_score FROM scores WHERE enrollment_id = ? ORDER BY kind, id",
        (enrollment_id,),
    ).fetchall()
    conn.close()

    result = compute_risk(rows)
    return render_template("student_detail.html", e=e, rows=rows, result=result)

TIPS = {
    "attendance": "Attendance is pulling your score down. Aim to attend every class from now on, since missed lectures add up quickly.",
    "assignment": "Assignments are your weakest area. Submit every outstanding one and ask your lecturer for feedback on the ones you lost marks on.",
    "test": "Tests are your weakest area. Review past test questions and form a short study group before the next one.",
}


@app.route("/my-course/<int:enrollment_id>")
def my_course(enrollment_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "student":
        return redirect(url_for("dashboard"))

    conn = get_db()
    # A student may only open their own enrollments
    e = conn.execute(
        """
        SELECT e.id, c.code, c.title
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.id = ? AND e.student_id = ?
        """,
        (enrollment_id, session["user_id"]),
    ).fetchone()
    if e is None:
        conn.close()
        abort(404)

    rows = conn.execute(
        "SELECT kind, label, score, max_score FROM scores WHERE enrollment_id = ? ORDER BY kind, id",
        (enrollment_id,),
    ).fetchall()
    conn.close()

    result = compute_risk(rows)
    tip = TIPS.get(result["weakest"]) if result else None
    return render_template("student_course.html", e=e, result=result, tip=tip)

@app.route("/enrollment/<int:enrollment_id>/add-score", methods=["POST"])
def add_score(enrollment_id):
    if "user_id" not in session or session["role"] != "lecturer":
        return redirect(url_for("login"))

    conn = get_db()
    # Only the lecturer who teaches the course may add scores
    owned = conn.execute(
        """
        SELECT e.id FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.id = ? AND c.lecturer_id = ?
        """,
        (enrollment_id, session["user_id"]),
    ).fetchone()
    if owned is None:
        conn.close()
        abort(404)

    kind = request.form["kind"]
    label = request.form["label"].strip()
    try:
        score = float(request.form["score"])
        max_score = float(request.form["max_score"])
    except ValueError:
        conn.close()
        flash("Score and maximum must be numbers.")
        return redirect(url_for("enrollment", enrollment_id=enrollment_id))

    if kind not in ("attendance", "assignment", "test") or max_score <= 0 or score < 0 or score > max_score:
        conn.close()
        flash("Invalid score. It must be between 0 and the maximum.")
        return redirect(url_for("enrollment", enrollment_id=enrollment_id))

    conn.execute(
        "INSERT INTO scores (enrollment_id, kind, label, score, max_score) VALUES (?,?,?,?,?)",
        (enrollment_id, kind, label, score, max_score),
    )
    conn.commit()
    conn.close()

    recompute_one(enrollment_id)
    flash("Score added and risk updated.")
    return redirect(url_for("enrollment", enrollment_id=enrollment_id))

if __name__ == "__main__":
    app.run(debug=True)