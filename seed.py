import random
from werkzeug.security import generate_password_hash
from db import get_db, init_db

random.seed(42)  # same fake data every time you run it

FIRST = ["Adaeze", "Tunde", "Blessing", "Chidi", "Ngozi", "Emeka", "Funke", "Ibrahim",
         "Amaka", "Kelechi", "Yusuf", "Chioma", "Segun", "Ifeoma", "Obinna",
         "Halima", "Uche", "Bola", "Nnamdi", "Zainab"]
LAST = ["Okafor", "Adeyemi", "Eze", "Nwosu", "Bello", "Ogunleye", "Okonkwo", "Musa"]

COURSES = [
    ("CSC 401", "Data Structures"),
    ("CSC 305", "Database Systems"),
    ("CSC 212", "Programming II"),
]

def seed():
    init_db()
    conn = get_db()

    # Clear old data (children first, parents last)
    for table in ["risk_assessments", "scores", "enrollments", "courses", "users"]:
        conn.execute(f"DELETE FROM {table}")

    pw = generate_password_hash("password123")

    # One lecturer
    conn.execute(
        "INSERT INTO users (name, email, password_hash, role, department) VALUES (?,?,?,?,?)",
        ("Dr. Nwosu", "lecturer@edupulse.test", pw, "lecturer", "Computer Science"),
    )
    lecturer_id = conn.execute("SELECT id FROM users WHERE role='lecturer'").fetchone()["id"]

    # Courses taught by that lecturer
    for code, title in COURSES:
        conn.execute(
            "INSERT INTO courses (code, title, lecturer_id) VALUES (?,?,?)",
            (code, title, lecturer_id),
        )
    course_ids = [r["id"] for r in conn.execute("SELECT id FROM courses")]

    # Students
    student_ids = []
    for i, first in enumerate(FIRST):
        name = f"{first} {random.choice(LAST)}"
        email = f"student{i+1}@edupulse.test"
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, role, matric_no, department) VALUES (?,?,?,?,?,?)",
            (name, email, pw, "student", f"2022/CS/{i+1:03d}", "Computer Science"),
        )
        student_ids.append(cur.lastrowid)

    # Enroll each student in 2 or 3 courses and generate scores
    for sid in student_ids:
        ability = random.uniform(0.35, 0.95)  # how strong this student is overall
        for cid in random.sample(course_ids, k=random.choice([2, 3])):
            cur = conn.execute(
                "INSERT INTO enrollments (student_id, course_id) VALUES (?,?)", (sid, cid)
            )
            eid = cur.lastrowid

            def noisy():
                return min(1.0, max(0.1, ability + random.uniform(-0.15, 0.15)))

            # Attendance: classes attended out of 20
            conn.execute(
                "INSERT INTO scores (enrollment_id, kind, label, score, max_score) VALUES (?,?,?,?,?)",
                (eid, "attendance", "Semester attendance", round(20 * noisy()), 20),
            )
            # 4 assignments out of 10
            for n in range(1, 5):
                conn.execute(
                    "INSERT INTO scores (enrollment_id, kind, label, score, max_score) VALUES (?,?,?,?,?)",
                    (eid, "assignment", f"Assignment {n}", round(10 * noisy(), 1), 10),
                )
            # 2 tests out of 20
            for n in range(1, 3):
                conn.execute(
                    "INSERT INTO scores (enrollment_id, kind, label, score, max_score) VALUES (?,?,?,?,?)",
                    (eid, "test", f"Test {n}", round(20 * noisy(), 1), 20),
                )

    conn.commit()
    conn.close()
    print("Seeded: 1 lecturer, 20 students, 3 courses.")
    print("Lecturer login: lecturer@edupulse.test / password123")
    print("Student login:  student1@edupulse.test / password123")

if __name__ == "__main__":
    seed()