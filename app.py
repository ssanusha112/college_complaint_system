from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)

# --------------------------------------------------

# Flask Secret Key

# --------------------------------------------------

app.secret_key = "college_complaint_secret_key_2026"

# --------------------------------------------------

# MySQL Database Connection

# --------------------------------------------------

def connect_db():
    return mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="college_complaint"
    )

# --------------------------------------------------

# Home / Login Page

# --------------------------------------------------

@app.route("/")
def home():
    return render_template("login.html")

# --------------------------------------------------
# Student Registration
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validation

        if not name:
            flash("Please enter your name!")
            return redirect(url_for("register"))

        if not email:
            flash("Please enter your email!")
            return redirect(url_for("register"))

        if not password:
            flash("Please enter a password!")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters!")
            return redirect(url_for("register"))

        db = connect_db()
        cursor = db.cursor()

        # Check existing email

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            db.close()

            flash("Email already registered!")

            return redirect(url_for("register"))

        # Create student

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password, role)
            VALUES (%s, %s, %s, %s)
            """,
            (
                name,
                email,
                password,
                "student"
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash("Registration successful! Please login.")

        return redirect(url_for("home"))

    return render_template("register.html")

# --------------------------------------------------

# Login

# --------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = %s AND password = %s
        """,
        (email, password)
    )

    user = cursor.fetchone()

    cursor.close()
    db.close()

    if user:
        # Store user information in session
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        # Admin
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))

        # Student
        return redirect(url_for("student_dashboard"))

    flash("Invalid email or password!")

    return redirect(url_for("home"))


# --------------------------------------------------
# Student Dashboard
# --------------------------------------------------

@app.route("/student/dashboard")
def student_dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("home"))

    # Only student
    if session["role"] != "student":
        return redirect(url_for("home"))

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    # Get student's complaints
    cursor.execute(
        """
        SELECT *
        FROM complaints
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    )

    complaints = cursor.fetchall()

    # Statistics
    total_complaints = len(complaints)

    pending = sum(
        1 for c in complaints
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints
        if c["status"] == "Resolved"
    )

    # Get notifications
    cursor.execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (session["user_id"],)
    )

    notifications = cursor.fetchall()

    # Count unread
    cursor.execute(
        """
        SELECT COUNT(*) AS unread
        FROM notifications
        WHERE user_id = %s
        AND is_read = 0
        """,
        (session["user_id"],)
    )

    unread = cursor.fetchone()["unread"]

    cursor.close()
    db.close()

    return render_template(
        "student_dashboard.html",
        complaints=complaints,
        total_complaints=total_complaints,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        notifications=notifications,
        unread=unread
    )

# --------------------------------------------------
# Submit Complaint
# --------------------------------------------------

@app.route("/complaint", methods=["GET", "POST"])
def complaint():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("home"))

    # Only students
    if session["role"] != "student":
        return redirect(url_for("home"))

    if request.method == "POST":

        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()

        # Validation
        if not category:
            flash("Please select a complaint category!")
            return redirect(url_for("complaint"))

        if not location:
            flash("Please enter the complaint location!")
            return redirect(url_for("complaint"))

        if not description:
            flash("Please enter the complaint description!")
            return redirect(url_for("complaint"))

        if len(description) < 10:
            flash("Complaint description must contain at least 10 characters!")
            return redirect(url_for("complaint"))

        # Database
        db = connect_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO complaints
            (user_id, category, location, description, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                category,
                location,
                description,
                "Pending"
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash("Complaint submitted successfully!")

        return redirect(url_for("student_dashboard"))

    return render_template("complaint.html")


# --------------------------------------------------
# Mark Notification as Read
# --------------------------------------------------

@app.route("/notification/read/<int:notification_id>")
def mark_notification_read(notification_id):

    # Check login
    if "user_id" not in session:
        return redirect(url_for("home"))

    # Only students
    if session["role"] != "student":
        return redirect(url_for("home"))

    db = connect_db()
    cursor = db.cursor()

    # Mark notification as read
    cursor.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = %s
        AND user_id = %s
        """,
        (
            notification_id,
            session["user_id"]
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        url_for("student_dashboard")
    )



# --------------------------------------------------
# Admin Dashboard
# --------------------------------------------------

@app.route("/admin/dashboard")
def admin_dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("home"))

    # Only admin can access
    if session["role"] != "admin":
        return redirect(url_for("home"))

    # Get search and filter values
    search = request.args.get("search", "")
    status_filter = request.args.get("status", "")

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    # Base query
    query = """
        SELECT
            complaints.*,
            users.name,
            users.email
        FROM complaints
        JOIN users
        ON complaints.user_id = users.id
        WHERE 1=1
    """

    values = []

    # Search
    if search:

        query += """
            AND (
                users.name LIKE %s
                OR users.email LIKE %s
                OR complaints.category LIKE %s
                OR complaints.location LIKE %s
            )
        """

        search_value = "%" + search + "%"

        values.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # Status filter
    if status_filter:

        query += """
            AND complaints.status = %s
        """

        values.append(status_filter)

    # Latest complaints first
    query += """
        ORDER BY complaints.created_at DESC
    """

    cursor.execute(query, values)

    complaints = cursor.fetchall()

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    total_complaints = len(complaints)

    pending = sum(
        1 for c in complaints
        if c["status"] == "Pending"
    )

    in_progress = sum(
        1 for c in complaints
        if c["status"] == "In Progress"
    )

    resolved = sum(
        1 for c in complaints
        if c["status"] == "Resolved"
    )

    rejected = sum(
        1 for c in complaints
        if c["status"] == "Rejected"
    )

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        total_complaints=total_complaints,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
        rejected=rejected,
        search=search,
        status_filter=status_filter
    )
# --------------------------------------------------
# Admin Update Complaint
# --------------------------------------------------

@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
def update_complaint(complaint_id):

    # Check login
    if "user_id" not in session:
        return redirect(url_for("home"))

    # Only admin
    if session["role"] != "admin":
        return redirect(url_for("home"))

    status = request.form.get("status", "").strip()

    admin_response = request.form.get(
        "admin_response",
        ""
    ).strip()

    # Allowed statuses

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved",
        "Rejected"
    ]

    if status not in allowed_statuses:

        flash("Invalid complaint status!")

        return redirect(
            url_for("admin_dashboard")
        )

    db = connect_db()
    cursor = db.cursor(dictionary=True)

    # Find complaint

    cursor.execute(
        """
        SELECT user_id
        FROM complaints
        WHERE id = %s
        """,
        (complaint_id,)
    )

    complaint = cursor.fetchone()

    if not complaint:

        cursor.close()
        db.close()

        flash("Complaint not found!")

        return redirect(
            url_for("admin_dashboard")
        )

    student_id = complaint["user_id"]

    # Update complaint

    cursor.execute(
        """
        UPDATE complaints
        SET status = %s,
            admin_response = %s
        WHERE id = %s
        """,
        (
            status,
            admin_response,
            complaint_id
        )
    )

    # Notification

    message = (
        f"Your complaint #{complaint_id} "
        f"has been updated to {status}."
    )

    if admin_response:

        message += (
            f" Admin response: {admin_response}"
        )

    cursor.execute(
        """
        INSERT INTO notifications
        (user_id, complaint_id, message)
        VALUES (%s, %s, %s)
        """,
        (
            student_id,
            complaint_id,
            message
        )
    )

    db.commit()

    cursor.close()
    db.close()

    flash("Complaint updated successfully!")

    return redirect(
        url_for("admin_dashboard")
    )
# --------------------------------------------------

# Logout

# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("home"))

# --------------------------------------------------

# Start Flask Application

# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
    )

