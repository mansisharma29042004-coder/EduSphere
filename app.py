
import os
from datetime import date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db_connection, initialize_database

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret")


# ---------------- DATABASE HELPER ----------------

def query_db(sql, values=(), fetch=True):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(sql, values)

        if fetch:
            result = cursor.fetchall()
            return result

        db.commit()
        return cursor.lastrowid

    finally:
        cursor.close()
        db.close()


# ---------------- ADMIN SECURITY ----------------

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper


# ---------------- PUBLIC PAGES ----------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admins = query_db(
            "SELECT * FROM admins WHERE username=%s",
            (username,)
        )

        if admins and check_password_hash(
            admins[0]["password_hash"], password
        ):
            session.clear()
            session["admin_id"] = admins[0]["id"]
            session["admin_name"] = admins[0]["full_name"]

            flash("Welcome to EduSphere Admin Panel!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("admin/admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("admin_login"))


# ---------------- DASHBOARD ----------------

@app.route("/admin/dashboard")
@admin_required
def dashboard():

    total_students = query_db(
        "SELECT COUNT(*) AS total FROM students"
    )[0]["total"]

    total_courses = query_db(
        "SELECT COUNT(*) AS total FROM courses"
    )[0]["total"]

    total_attendance = query_db(
        "SELECT COUNT(*) AS total FROM attendance "
        "WHERE attendance_status='Present' AND attendance_date=%s",
        (date.today(),)
    )[0]["total"]

    fee_data = query_db(
        "SELECT COALESCE(SUM(paid_amount),0) AS total FROM fees"
    )[0]["total"]

    recent_students = query_db(
        "SELECT s.*, c.course_name FROM students s "
        "LEFT JOIN courses c ON s.course_id=c.id "
        "ORDER BY s.id DESC LIMIT 5"
    )

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        total_attendance=total_attendance,
        fee_data=fee_data,
        recent_students=recent_students
    )


# ---------------- STUDENT MANAGEMENT ----------------

@app.route("/admin/students")
@admin_required
def students():
    search = request.args.get("search", "").strip()

    if search:
        student_list = query_db(
            """
            SELECT s.*, c.course_name
            FROM students s
            LEFT JOIN courses c ON s.course_id=c.id
            WHERE s.first_name LIKE %s
               OR s.last_name LIKE %s
               OR s.email LIKE %s
               OR s.admission_no LIKE %s
            ORDER BY s.id DESC
            """,
            tuple([f"%{search}%"] * 4)
        )
    else:
        student_list = query_db(
            """
            SELECT s.*, c.course_name
            FROM students s
            LEFT JOIN courses c ON s.course_id=c.id
            ORDER BY s.id DESC
            """
        )

    return render_template(
        "admin/students.html",
        students=student_list,
        search=search
    )


@app.route("/admin/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        try:
            query_db(
                """
                INSERT INTO students
                (admission_no, first_name, last_name, email,
                 phone, gender, date_of_birth, address,
                 course_id, admission_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    request.form["admission_no"],
                    request.form["first_name"],
                    request.form.get("last_name"),
                    request.form["email"],
                    request.form.get("phone"),
                    request.form.get("gender"),
                    request.form.get("date_of_birth") or None,
                    request.form.get("address"),
                    request.form.get("course_id") or None,
                    request.form.get("admission_date") or None
                ),
                fetch=False
            )
            flash("Student added successfully!", "success")
            return redirect(url_for("students"))

        except Exception as error:
            flash(f"Unable to add student: {error}", "danger")

    courses = query_db("SELECT * FROM courses ORDER BY course_name")
    return render_template(
        "admin/student_form.html",
        student=None,
        courses=courses
    )


@app.route("/admin/students/edit/<int:student_id>",
           methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    student_data = query_db(
        "SELECT * FROM students WHERE id=%s",
        (student_id,)
    )

    if not student_data:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    student = student_data[0]

    if request.method == "POST":
        try:
            query_db(
                """
                UPDATE students SET
                admission_no=%s, first_name=%s, last_name=%s,
                email=%s, phone=%s, gender=%s,
                date_of_birth=%s, address=%s, course_id=%s,
                admission_date=%s, status=%s
                WHERE id=%s
                """,
                (
                    request.form["admission_no"],
                    request.form["first_name"],
                    request.form.get("last_name"),
                    request.form["email"],
                    request.form.get("phone"),
                    request.form.get("gender"),
                    request.form.get("date_of_birth") or None,
                    request.form.get("address"),
                    request.form.get("course_id") or None,
                    request.form.get("admission_date") or None,
                    request.form.get("status", "Active"),
                    student_id
                ),
                fetch=False
            )

            flash("Student updated successfully!", "success")
            return redirect(url_for("students"))

        except Exception as error:
            flash(f"Unable to update student: {error}", "danger")

    courses = query_db("SELECT * FROM courses ORDER BY course_name")

    return render_template(
        "admin/student_form.html",
        student=student,
        courses=courses
    )


@app.route("/admin/students/delete/<int:student_id>",
           methods=["POST"])
@admin_required
def delete_student(student_id):
    query_db(
        "DELETE FROM students WHERE id=%s",
        (student_id,),
        fetch=False
    )
    flash("Student deleted successfully!", "success")
    return redirect(url_for("students"))


# ---------------- COURSES ----------------

@app.route("/admin/courses")
@admin_required
def courses():
    course_list = query_db(
        """
        SELECT c.*, d.department_name
        FROM courses c
        LEFT JOIN departments d ON c.department_id=d.id
        ORDER BY c.id DESC
        """
    )
    return render_template("admin/courses.html", courses=course_list)


# ---------------- ATTENDANCE ----------------

@app.route("/admin/attendance", methods=["GET", "POST"])
@admin_required
def attendance():

    if request.method == "POST":
        try:
            query_db(
                """
                INSERT INTO attendance
                (student_id, attendance_date, attendance_status, remarks)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                attendance_status=VALUES(attendance_status),
                remarks=VALUES(remarks)
                """,
                (
                    request.form["student_id"],
                    request.form.get("attendance_date") or str(date.today()),
                    request.form["attendance_status"],
                    request.form.get("remarks")
                ),
                fetch=False
            )
            flash("Attendance saved successfully!", "success")
        except Exception as error:
            flash(f"Attendance error: {error}", "danger")

        return redirect(url_for("attendance"))

    students_list = query_db(
        "SELECT id, admission_no, first_name, last_name "
        "FROM students ORDER BY first_name"
    )

    records = query_db(
        """
        SELECT a.*, s.admission_no, s.first_name, s.last_name
        FROM attendance a
        JOIN students s ON a.student_id=s.id
        ORDER BY a.attendance_date DESC, a.id DESC LIMIT 100
        """
    )

    return render_template(
        "admin/attendance.html",
        students=students_list,
        records=records
    )


# ---------------- FEES ----------------

@app.route("/admin/fees", methods=["GET", "POST"])
@admin_required
def fees():

    if request.method == "POST":
        try:
            total = float(request.form["total_fee"])
            paid = float(request.form["paid_amount"])

            if total <= 0 or paid < 0 or paid > total:
                raise ValueError("Invalid fee amount.")

            status = "Paid" if paid == total else (
                "Partial" if paid > 0 else "Pending"
            )

            query_db(
                """
                INSERT INTO fees
                (student_id, total_fee, paid_amount,
                 payment_date, payment_method,
                 transaction_id, payment_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    request.form["student_id"],
                    total,
                    paid,
                    request.form.get("payment_date") or None,
                    request.form.get("payment_method"),
                    request.form.get("transaction_id"),
                    status
                ),
                fetch=False
            )

            flash("Fee record saved successfully!", "success")

        except Exception as error:
            flash(f"Fee error: {error}", "danger")

        return redirect(url_for("fees"))

    students_list = query_db(
        "SELECT id, admission_no, first_name, last_name FROM students"
    )

    records = query_db(
        """
        SELECT f.*, s.first_name, s.last_name, s.admission_no
        FROM fees f JOIN students s ON f.student_id=s.id
        ORDER BY f.id DESC
        """
    )

    return render_template(
        "admin/fees.html",
        students=students_list,
        records=records
    )


# ---------------- RESULTS ----------------

@app.route("/admin/results", methods=["GET", "POST"])
@admin_required
def results():

    if request.method == "POST":
        try:
            total = float(request.form["total_marks"])
            obtained = float(request.form["obtained_marks"])

            if total <= 0 or obtained < 0 or obtained > total:
                raise ValueError("Invalid marks entered.")

            query_db(
                """
                INSERT INTO results
                (student_id, exam_name, subject,
                 total_marks, obtained_marks, exam_date)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    request.form["student_id"],
                    request.form["exam_name"],
                    request.form["subject"],
                    total,
                    obtained,
                    request.form.get("exam_date") or None
                ),
                fetch=False
            )
            flash("Result saved successfully!", "success")

        except Exception as error:
            flash(f"Result error: {error}", "danger")

        return redirect(url_for("results"))

    students_list = query_db(
        "SELECT id, admission_no, first_name, last_name FROM students"
    )

    records = query_db(
        """
        SELECT r.*, s.first_name, s.last_name, s.admission_no
        FROM results r JOIN students s ON r.student_id=s.id
        ORDER BY r.id DESC
        """
    )

    return render_template(
        "admin/results.html",
        students=students_list,
        records=records
    )


# ---------------- REPORTS ----------------

@app.route("/admin/reports")
@admin_required
def reports():
    report_data = query_db(
        """
        SELECT
        (SELECT COUNT(*) FROM students) AS students,
        (SELECT COUNT(*) FROM courses) AS courses,
        (SELECT COUNT(*) FROM attendance
         WHERE attendance_status='Present') AS present_records,
        (SELECT COALESCE(SUM(paid_amount),0) FROM fees) AS collection
        """
    )[0]

    return render_template(
        "admin/reports.html",
        report=report_data
    )


# ---------------- ERROR HANDLING ----------------

@app.errorhandler(404)
def page_not_found(error):
    return "Page not found. Please check the URL.", 404


if __name__ == "__main__":
    initialize_database()
    print("Admin username: " + os.getenv("ADMIN_USERNAME", "admin"))
    print("Admin password: " + os.getenv("ADMIN_PASSWORD", "Edu@Admin123"))
    app.run(debug=True)
