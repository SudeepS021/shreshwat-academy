
import os
import sqlite3
import uuid

from functools import wraps
from io import BytesIO
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, jsonify, send_file
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "shreshwat.db")

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-before-deployment"
)

# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():

    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row

    return g.db

@app.teardown_appcontext
def close_db(error=None):

    db = g.pop("db", None)

    if db is not None:
        db.close()

# ==========================================
# DATABASE TABLES
# ==========================================

def init_db():

    with sqlite3.connect(DATABASE) as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id TEXT NOT NULL,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, course_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS python_channel_access (
                user_id INTEGER PRIMARY KEY,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS python_video_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chapter_number INTEGER NOT NULL,
                watched_seconds REAL DEFAULT 0,
                video_duration REAL DEFAULT 0,
                completed INTEGER DEFAULT 0,
                UNIQUE(user_id, chapter_number),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS python_quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chapter_number INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS python_final_exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                certificate_id TEXT NOT NULL UNIQUE,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Safe migration: existing accounts receive NULL DOB and keep all data.
        user_columns = {
            row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()
        }
        if "dob" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN dob TEXT")

        # Track password-reset attempts to slow repeated guesses.
        db.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# ==========================================
# LOGIN PROTECTION
# ==========================================

def login_required(view):

    @wraps(view)
    def wrapped_view(**kwargs):

        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))

        return view(**kwargs)

    return wrapped_view

# ==========================================
# PYTHON CHAPTERS
# ==========================================

PYTHON_CHAPTERS = [

    {"number": 1, "title": "Introduction to Python",
     "video_id": "Ke-SVlpUVYs"},

    {"number": 2, "title": "Variables and Datatypes",
     "video_id": "w2-TquKhGX8"},

    {"number": 3, "title": "Strings",
     "video_id": "bUHQLdL5F-c"},

    {"number": 4, "title": "Lists and Tuples",
     "video_id": "JdNDBq9tL9M"},

    {"number": 5, "title": "Dictionary and Sets",
     "video_id": "gJjMT9l-5fQ"},

    {"number": 6, "title": "Conditional Expression",
     "video_id": "Oi_YoDSUjnc"},

    {"number": 7, "title": "Loops in Python",
     "video_id": "qG80FgQZbbs"},

    {"number": 8, "title": "Functions and Recursions",
     "video_id": "UVfmfQ-M_bI"},

    {"number": 9, "title": "File I/O",
     "video_id": "mfBKoj67snM"},

    {"number": 10, "title": "Object Oriented Programming",
     "video_id": "UFno_f3AHgo"},

    {"number": 11, "title": "Inheritance",
     "video_id": "F8nc9Q5T-VY"}
]

# ==========================================
# QUIZ QUESTION HELPER
# ==========================================

def make_question(question, a, b, c, d, answer):

    return {
        "question": question,
        "options": {
            "A": a,
            "B": b,
            "C": c,
            "D": d
        },
        "answer": answer
    }

# ==========================================
# ALL 11 CHAPTER QUIZZES
# 5 QUESTIONS PER CHAPTER
# ==========================================

QUIZZES = {

    1: [
        make_question("What is programming?",
                      "Giving instructions to a computer",
                      "Playing games",
                      "Installing hardware",
                      "Browsing the internet", "A"),

        make_question("Which is a major use of Python?",
                      "Only typing documents",
                      "Artificial Intelligence and Data Science",
                      "Only playing games",
                      "Only operating a keyboard", "B"),

        make_question("What is a Python module?",
                      "A computer monitor",
                      "A variable",
                      "A file containing reusable code",
                      "A Python error", "C"),

        make_question("What is pip used for?",
                      "Creating variables",
                      "Printing output",
                      "Writing comments",
                      "Installing Python packages", "D"),

        make_question("What does REPL stand for?",
                      "Read Evaluate Print Loop",
                      "Run Execute Program Language",
                      "Read Edit Python Library",
                      "Repeat Every Programming Line", "A")
    ],

    2: [
        make_question("What is a variable?",
                      "A loop",
                      "A name used to store a value",
                      "A comment",
                      "A module", "B"),

        make_question("Which is a valid Python data type?",
                      "Keyboard",
                      "Monitor",
                      "Integer",
                      "Folder", "C"),

        make_question("Which variable name is invalid?",
                      "student",
                      "_student",
                      "student2",
                      "2student", "D"),

        make_question("What does type() do?",
                      "Finds the data type of a value",
                      "Deletes a variable",
                      "Creates a loop",
                      "Prints a comment", "A"),

        make_question("What type of value does input() return by default?",
                      "Integer",
                      "String",
                      "Boolean",
                      "Float", "B")
    ],

    3: [
        make_question("What is a string?",
                      "A loop",
                      "A numeric operator",
                      "A sequence of characters",
                      "A class", "C"),

        make_question("What is the first index of a Python string?",
                      "1",
                      "-1",
                      "2",
                      "0", "D"),

        make_question("What does len('Python') return?",
                      "6",
                      "5",
                      "7",
                      "4", "A"),

        make_question("Which method replaces text in a string?",
                      "find()",
                      "replace()",
                      "count()",
                      "endswith()", "B"),

        make_question("Which symbol is used for a single-line comment?",
                      "@",
                      "$",
                      "#",
                      "&", "C")
    ],

    4: [
        make_question("Which data structure is mutable?",
                      "Tuple",
                      "String",
                      "Integer",
                      "List", "D"),

        make_question("Which list method adds an element at the end?",
                      "append()",
                      "remove()",
                      "pop()",
                      "sort()", "A"),

        make_question("Which method sorts a list?",
                      "reverse()",
                      "sort()",
                      "insert()",
                      "clear()", "B"),

        make_question("Which statement about tuples is correct?",
                      "Tuples are mutable",
                      "Tuples are dictionaries",
                      "Tuples are immutable",
                      "Tuples cannot store numbers", "C"),

        make_question("How do you create a single-element tuple?",
                      "(1)",
                      "[1]",
                      "{1}",
                      "(1,)", "D")
    ],

    5: [
        make_question("What does a dictionary store?",
                      "Key-value pairs",
                      "Only strings",
                      "Only integers",
                      "Only lists", "A"),

        make_question("Which dictionary method returns its keys?",
                      "items()",
                      "keys()",
                      "values()",
                      "clear()", "B"),

        make_question("Can a Python set contain duplicate values?",
                      "Yes, always",
                      "Only numbers",
                      "No",
                      "Only strings", "C"),

        make_question("Which set method returns common elements?",
                      "union()",
                      "add()",
                      "remove()",
                      "intersection()", "D"),

        make_question("Which creates an empty set?",
                      "set()",
                      "{}",
                      "[]",
                      "()", "A")
    ],

    6: [
        make_question("Which keyword is used for a condition?",
                      "for",
                      "if",
                      "def",
                      "class", "B"),

        make_question("What does elif mean?",
                      "End loop",
                      "Exit function",
                      "Else if",
                      "Execute file", "C"),

        make_question("Which operator checks equality?",
                      "=",
                      "!=",
                      "+=",
                      "==", "D"),

        make_question("When does and return True?",
                      "When both conditions are True",
                      "When both are False",
                      "When either is False",
                      "Always", "A"),

        make_question("What does not do?",
                      "Adds values",
                      "Inverts a Boolean value",
                      "Repeats a loop",
                      "Creates a list", "B")
    ],

    7: [
        make_question("What is the purpose of a loop?",
                      "To define a class",
                      "To import a module",
                      "To repeat instructions",
                      "To create a comment", "C"),

        make_question("Which are the main loop types in Python?",
                      "if and else",
                      "try and except",
                      "class and object",
                      "for and while", "D"),

        make_question("What values are generated by range(5)?",
                      "0, 1, 2, 3, 4",
                      "1, 2, 3, 4, 5",
                      "0, 1, 2, 3, 4, 5",
                      "Only 5", "A"),

        make_question("What does break do?",
                      "Skips one iteration",
                      "Exits the loop",
                      "Restarts the loop",
                      "Defines a function", "B"),

        make_question("What does continue do?",
                      "Ends the program",
                      "Deletes a loop",
                      "Skips the current iteration",
                      "Creates a class", "C")
    ],

    8: [
        make_question("Which keyword defines a function?",
                      "class",
                      "return",
                      "import",
                      "def", "D"),

        make_question("What is a function?",
                      "A group of statements performing a task",
                      "A data type",
                      "A comment",
                      "A variable", "A"),

        make_question("Which is a built-in Python function?",
                      "myTask()",
                      "len()",
                      "studentTask()",
                      "greetUser()", "B"),

        make_question("What does return do?",
                      "Creates a loop",
                      "Imports a module",
                      "Sends a value back to the caller",
                      "Deletes a variable", "C"),

        make_question("What is recursion?",
                      "A class inheriting another class",
                      "A list inside a list",
                      "A variable declaration",
                      "A function calling itself", "D")
    ],

    9: [
        make_question("Why are files used?",
                      "To preserve data",
                      "To create loops",
                      "To install Python",
                      "To define classes", "A"),

        make_question("Which function opens a file?",
                      "read()",
                      "open()",
                      "print()",
                      "input()", "B"),

        make_question("Which mode opens a file for reading?",
                      "w",
                      "a",
                      "r",
                      "+", "C"),

        make_question("Which method reads file content?",
                      "write()",
                      "close()",
                      "open()",
                      "read()", "D"),

        make_question("What does with help with when opening files?",
                      "Managing file closing automatically",
                      "Creating a class",
                      "Deleting a file",
                      "Installing a package", "A")
    ],

    10: [
        make_question("What is a class?",
                      "A loop",
                      "A blueprint for creating objects",
                      "A string",
                      "A module", "B"),

        make_question("What is an object?",
                      "A comment",
                      "A function only",
                      "An instance of a class",
                      "A Python package", "C"),

        make_question("What is a class attribute?",
                      "A local variable only",
                      "A temporary variable",
                      "A loop variable",
                      "An attribute shared through the class", "D"),

        make_question("What does self refer to?",
                      "The current object instance",
                      "The parent module",
                      "The class file",
                      "The Python interpreter", "A"),

        make_question("When is __init__() called?",
                      "When a loop ends",
                      "When an object is created",
                      "When a file closes",
                      "When a module is installed", "B")
    ],

    11: [
        make_question("What is inheritance?",
                      "Deleting a class",
                      "Creating a list",
                      "Creating a class from an existing class",
                      "Importing a module", "C"),

        make_question("What is a derived class?",
                      "The base class",
                      "An unrelated class",
                      "A built-in function",
                      "A child class that inherits from another class", "D"),

        make_question("What is single inheritance?",
                      "A child class inherits from one parent class",
                      "A class has no parent",
                      "A class inherits from many parents",
                      "A function calls itself", "A"),

        make_question("What is multiple inheritance?",
                      "One parent with many objects",
                      "A child class inherits from multiple parent classes",
                      "A class with no methods",
                      "A function calling itself", "B"),

        make_question("What is super() commonly used for?",
                      "Deleting a class",
                      "Creating a list",
                      "Accessing methods of a superclass",
                      "Printing a variable", "C")
    ]
}

# ==========================================
# FINAL EXAM - 50 QUESTIONS
# ==========================================

FINAL_EXAM_QUESTIONS = [

    ("What is programming?",
     ["Giving instructions to a computer", "Playing games", "Installing hardware", "Browsing the internet"], "A"),

    ("Which language is commonly used in AI and Data Science?",
     ["HTML", "Python", "CSS", "XML"], "B"),

    ("What is a Python module?",
     ["A variable", "A loop", "A file containing reusable code", "A data type"], "C"),

    ("What is pip used for?",
     ["Printing output", "Creating variables", "Writing comments", "Installing Python packages"], "D"),

    ("What does REPL stand for?",
     ["Read Evaluate Print Loop", "Run Execute Program Language", "Read Edit Python Library", "Repeat Every Programming Line"], "A"),

    ("What is a variable?",
     ["A loop", "A name used to store a value", "A comment", "A module"], "B"),

    ("Which is an integer?",
     ["10.5", '"Hello"', "25", "True"], "C"),

    ("Which is a valid variable name?",
     ["2name", "my name", "class", "_student"], "D"),

    ("What does type() return?",
     ["Data type", "Variable value only", "Memory size", "File name"], "A"),

    ("What does input() return by default?",
     ["Integer", "String", "Float", "Boolean"], "B"),

    ("What is a string?",
     ["A loop", "A number", "A sequence of characters", "A function"], "C"),

    ("What is the first index of a Python string?",
     ["1", "-1", "2", "0"], "D"),

    ("What does len('Python') return?",
     ["6", "5", "7", "4"], "A"),

    ("Which method replaces text in a string?",
     ["find()", "replace()", "count()", "endswith()"], "B"),

    ("Which symbol is used for a single-line comment?",
     ["@", "$", "#", "&"], "C"),

    ("Which data structure is mutable?",
     ["Tuple", "String", "Integer", "List"], "D"),

    ("Which list method adds an element at the end?",
     ["append()", "remove()", "pop()", "sort()"], "A"),

    ("Which method sorts a list?",
     ["reverse()", "sort()", "insert()", "clear()"], "B"),

    ("Which statement about tuples is correct?",
     ["Tuples are mutable", "Tuples are dictionaries", "Tuples are immutable", "Tuples cannot store numbers"], "C"),

    ("How do you create a single-element tuple?",
     ["(1)", "[1]", "{1}", "(1,)"], "D"),

    ("What does a dictionary store?",
     ["Key-value pairs", "Only strings", "Only integers", "Only lists"], "A"),

    ("Which dictionary method returns its keys?",
     ["items()", "keys()", "values()", "clear()"], "B"),

    ("Can a Python set contain duplicate values?",
     ["Yes, always", "Only numbers", "No", "Only strings"], "C"),

    ("Which set method returns common elements?",
     ["union()", "add()", "remove()", "intersection()"], "D"),

    ("Which creates an empty set?",
     ["set()", "{}", "[]", "()"], "A"),

    ("Which keyword is used for a condition?",
     ["for", "if", "import", "class"], "B"),

    ("What does elif mean?",
     ["End loop", "Exit function", "Else if", "Execute file"], "C"),

    ("Which operator checks equality?",
     ["=", "!=", "+=", "=="], "D"),

    ("What does the and operator require for True?",
     ["Both conditions must be True", "One condition must be True", "Both must be False", "Neither condition matters"], "A"),

    ("What does not do?",
     ["Adds values", "Inverts a Boolean value", "Repeats a loop", "Creates a list"], "B"),

    ("What is the purpose of a loop?",
     ["To define a class", "To import a module", "To repeat instructions", "To create a comment"], "C"),

    ("Which are the main loop types in Python?",
     ["if and else", "try and except", "class and object", "for and while"], "D"),

    ("What values are generated by range(5)?",
     ["0, 1, 2, 3, 4", "1, 2, 3, 4, 5", "0, 1, 2, 3, 4, 5", "Only 5"], "A"),

    ("What does break do?",
     ["Skips one iteration", "Exits the loop", "Restarts the loop", "Defines a function"], "B"),

    ("What does continue do?",
     ["Ends the program", "Deletes a loop", "Skips the current iteration", "Creates a class"], "C"),

    ("Which keyword defines a function?",
     ["class", "return", "import", "def"], "D"),

    ("What is a function?",
     ["A group of statements performing a task", "A data type", "A comment", "A variable"], "A"),

    ("Which is a built-in Python function?",
     ["myTask()", "len()", "studentTask()", "greetUser()"], "B"),

    ("What does return do?",
     ["Creates a loop", "Imports a module", "Sends a value back to the caller", "Deletes a variable"], "C"),

    ("What is recursion?",
     ["A class inheriting another class", "A list inside a list", "A variable declaration", "A function calling itself"], "D"),

    ("Why are files used?",
     ["To preserve data", "To create loops", "To install Python", "To define classes"], "A"),

    ("Which function opens a file?",
     ["read()", "open()", "print()", "input()"], "B"),

    ("Which mode opens a file for reading?",
     ["w", "a", "r", "+"], "C"),

    ("Which method reads the entire file content?",
     ["write()", "close()", "open()", "read()"], "D"),

    ("What is the purpose of the with statement when opening files?",
     ["It helps manage file closing automatically", "It creates a class", "It deletes the file", "It installs a package"], "A"),

    ("What is a class?",
     ["A loop", "A blueprint for creating objects", "A variable", "A module"], "B"),

    ("What is an object?",
     ["A comment", "A function only", "An instance of a class", "A Python package"], "C"),

    ("What does self refer to?",
     ["The parent module", "The class file", "The Python interpreter", "The current object instance"], "D"),

    ("When is __init__() called?",
     ["When an object is created", "When a loop ends", "When a file closes", "When a module is installed"], "A"),

    ("What is inheritance?",
     ["Deleting a class", "Creating a class from an existing class", "Creating a list", "Importing a module"], "B"),

    ("What is multiple inheritance?",
     ["One class with no parent", "A function calling itself", "A child class inheriting from multiple parent classes", "A loop inside a loop"], "C")
]

def get_final_exam_questions():

    questions = []

    for question, options, answer in FINAL_EXAM_QUESTIONS:

        questions.append({
            "question": question,
            "options": {
                "A": options[0],
                "B": options[1],
                "C": options[2],
                "D": options[3]
            },
            "answer": answer
        })

    return questions

# ==========================================
# DATABASE CHECK HELPERS
# ==========================================

def is_python_enrolled():

    return get_db().execute(
        """
        SELECT id FROM enrollments
        WHERE user_id = ? AND course_id = 'python'
        """,
        (session["user_id"],)
    ).fetchone() is not None

def video_completed(chapter_number):

    row = get_db().execute(
        """
        SELECT completed
        FROM python_video_progress
        WHERE user_id = ? AND chapter_number = ?
        """,
        (session["user_id"], chapter_number)
    ).fetchone()

    return bool(row and row["completed"])

def quiz_passed(chapter_number):

    row = get_db().execute(
        """
        SELECT id
        FROM python_quiz_attempts
        WHERE user_id = ?
          AND chapter_number = ?
          AND passed = 1
        LIMIT 1
        """,
        (session["user_id"], chapter_number)
    ).fetchone()

    return row is not None

def chapter_unlocked(chapter_number):

    # Chapter 1 is available to every enrolled Python student.
    # Chapters 2-11 unlock after passing the previous chapter quiz.
    if chapter_number == 1:
        return True

    return quiz_passed(chapter_number - 1)

def all_python_quizzes_passed():

    for number in range(1, 12):

        if not quiz_passed(number):
            return False

    return True

def get_certificate():

    return get_db().execute(
        """
        SELECT certificate_id, issued_at
        FROM certificates
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()

# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")

# ==========================================
# COURSES PAGE
# ==========================================

@app.route("/courses")
def courses():
    return render_template("courses.html")

# ==========================================
# REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        dob = request.form.get("dob", "").strip()

        try:
            parsed_dob = datetime.strptime(dob, "%Y-%m-%d").date()
            valid_dob = parsed_dob < datetime.now().date()
        except ValueError:
            valid_dob = False

        if not name or not email or not password or not dob:
            flash("Please fill in every field.", "error")

        elif not valid_dob:
            flash("Please enter a valid date of birth in the past.", "error")

        elif len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")

        else:

            try:

                db = get_db()

                db.execute(
                    """
                    INSERT INTO users (name, email, password_hash, dob)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, email, generate_password_hash(password), dob)
                )

                db.commit()

                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))

            except sqlite3.IntegrityError:

                flash(
                    "An account with that email already exists.",
                    "error"
                )

    return render_template("register.html")

# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.", "error")

    return render_template("login.html")

# ==========================================
# FORGOT PASSWORD
# ==========================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        dob = request.form.get("dob", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        ip_address = request.remote_addr or "unknown"
        db = get_db()

        # Allow at most 5 reset submissions per IP in a 15-minute window.
        db.execute(
            "DELETE FROM password_reset_attempts "
            "WHERE attempted_at < datetime('now', '-15 minutes')"
        )
        attempts = db.execute(
            """SELECT COUNT(*) AS total FROM password_reset_attempts
               WHERE ip_address = ?
                 AND attempted_at >= datetime('now', '-15 minutes')""",
            (ip_address,)
        ).fetchone()["total"]

        if attempts >= 5:
            flash("Too many attempts. Please try again after 15 minutes.", "error")
            return render_template("forgot_password.html")

        db.execute(
            "INSERT INTO password_reset_attempts (ip_address) VALUES (?)",
            (ip_address,)
        )
        db.commit()

        if not email or not dob or not new_password or not confirm_password:
            flash("Please fill in every field.", "error")
            return render_template("forgot_password.html")

        if len(new_password) < 8:
            flash("Use a password with at least 8 characters.", "error")
            return render_template("forgot_password.html")

        if new_password != confirm_password:
            flash("The new passwords do not match.", "error")
            return render_template("forgot_password.html")

        user = db.execute(
            "SELECT id, dob FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        # Keep the message generic so account details are not disclosed.
        if not user or not user["dob"] or user["dob"] != dob:
            flash(
                "The details could not be verified. If your account was created "
                "before date-of-birth verification was added, contact the academy "
                "administrator for help.",
                "error"
            )
            return render_template("forgot_password.html")

        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user["id"])
        )
        db.commit()

        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# ==========================================
# ENROLLMENT
# ==========================================

@app.route("/enroll/<course_id>", methods=["POST"])
@login_required
def enroll(course_id):

    if course_id not in ["python", "c"]:
        flash("Invalid course selected.", "error")
        return redirect(url_for("courses"))

    db = get_db()

    try:

        db.execute(
            """
            INSERT INTO enrollments (user_id, course_id)
            VALUES (?, ?)
            """,
            (session["user_id"], course_id)
        )

        db.commit()

        course_name = (
            "Python Programming"
            if course_id == "python"
            else "C Programming"
        )

        flash(f"Successfully enrolled in {course_name}!", "success")

    except sqlite3.IntegrityError:

        flash("You are already enrolled in this course.", "info")

    return redirect(url_for("dashboard"))

# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    enrolled_courses = get_db().execute(
        """
        SELECT course_id, enrolled_at
        FROM enrollments
        WHERE user_id = ?
        ORDER BY enrolled_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name", "Student"),
        enrolled_courses=enrolled_courses
    )

# ==========================================
# PYTHON COURSE PAGE
# ==========================================

@app.route("/course/python")
@login_required
def python_course():

    if not is_python_enrolled():

        flash("Please enroll in Python Programming first.", "info")
        return redirect(url_for("courses"))

    db = get_db()
    course_data = []

    for chapter in PYTHON_CHAPTERS:

        number = chapter["number"]

        progress = db.execute(
            """
            SELECT watched_seconds, video_duration, completed
            FROM python_video_progress
            WHERE user_id = ? AND chapter_number = ?
            """,
            (session["user_id"], number)
        ).fetchone()

        if progress:

            progress = dict(progress)

        else:

            progress = {
                "watched_seconds": 0,
                "video_duration": 0,
                "completed": 0
            }

        unlocked = chapter_unlocked(number)
        passed = quiz_passed(number)

        latest_attempt = db.execute(
            """
            SELECT score, total_questions, passed
            FROM python_quiz_attempts
            WHERE user_id = ? AND chapter_number = ?
            ORDER BY id DESC LIMIT 1
            """,
            (session["user_id"], number)
        ).fetchone()

        item = dict(chapter)

        item["unlocked"] = unlocked
        item["progress"] = progress
        item["quiz_passed"] = passed
        item["latest_attempt"] = latest_attempt

        course_data.append(item)

    return render_template(
        "python_course.html",
        chapters=course_data,
        youtube_channel_url="https://youtube.com/@shreshwat_academy",
        user_name=session.get("user_name", "Student"),
        course_completed=all_python_quizzes_passed(),
        certificate=get_certificate()
    )

# ==========================================
# SAVE VIDEO PROGRESS
# ==========================================

@app.route(
    "/course/python/save-progress/<int:chapter_number>",
    methods=["POST"]
)
@login_required
def save_python_progress(chapter_number):

    if not is_python_enrolled():
        return jsonify({"error": "Not enrolled"}), 403

    if chapter_number < 1 or chapter_number > 11:
        return jsonify({"error": "Invalid chapter"}), 404

    if not chapter_unlocked(chapter_number):
        return jsonify({"error": "Chapter is locked"}), 403

    data = request.get_json(silent=True) or {}

    try:

        seconds = float(data.get("seconds", 0))
        duration = float(data.get("duration", 0))

    except (TypeError, ValueError):

        return jsonify({"error": "Invalid progress"}), 400

    if (
        seconds <= 0
        or seconds > 7
        or duration <= 0
        or duration > 86400
    ):

        return jsonify({"error": "Invalid progress values"}), 400

    db = get_db()

    old = db.execute(
        """
        SELECT watched_seconds, completed
        FROM python_video_progress
        WHERE user_id = ? AND chapter_number = ?
        """,
        (session["user_id"], chapter_number)
    ).fetchone()

    if old and old["completed"]:

        return jsonify({
            "completed": True,
            "percent": 100
        })

    old_seconds = old["watched_seconds"] if old else 0

    watched = min(old_seconds + seconds, duration)

    completed = int(watched >= duration * 0.80)

    db.execute(
        """
        INSERT INTO python_video_progress
        (user_id, chapter_number, watched_seconds,
         video_duration, completed)
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(user_id, chapter_number)
        DO UPDATE SET
            watched_seconds = MAX(
                python_video_progress.watched_seconds,
                excluded.watched_seconds
            ),
            video_duration = excluded.video_duration,
            completed = MAX(
                python_video_progress.completed,
                excluded.completed
            )
        """,
        (
            session["user_id"],
            chapter_number,
            watched,
            duration,
            completed
        )
    )

    db.commit()

    percent = min(100, int((watched / duration) * 100))

    return jsonify({
        "completed": bool(completed),
        "percent": percent
    })

# ==========================================
# ALL 11 CHAPTER QUIZZES
# ==========================================

@app.route(
    "/course/python/quiz/<int:chapter_number>",
    methods=["GET", "POST"]
)
@login_required
def python_quiz(chapter_number):

    if not is_python_enrolled():

        flash("Please enroll in Python Programming first.", "info")
        return redirect(url_for("courses"))

    if chapter_number not in QUIZZES:

        flash("Invalid quiz.", "error")
        return redirect(url_for("python_course"))

    if not video_completed(chapter_number):

        flash(
            f"Complete Chapter {chapter_number} video first.",
            "info"
        )

        return redirect(url_for("python_course"))

    if quiz_passed(chapter_number):

        flash(
            f"You have already passed Quiz {chapter_number}!",
            "success"
        )

        return redirect(url_for("python_course"))

    questions = QUIZZES[chapter_number]

    if request.method == "POST":

        answers = []

        for number in range(1, 6):

            answer = request.form.get(f"q{number}")

            if answer not in ["A", "B", "C", "D"]:

                flash("Please answer all five questions.", "error")

                return redirect(
                    url_for(
                        "python_quiz",
                        chapter_number=chapter_number
                    )
                )

            answers.append(answer)

        score = sum(
            answers[index] == questions[index]["answer"]
            for index in range(5)
        )

        passed = int(score >= 4)

        db = get_db()

        db.execute(
            """
            INSERT INTO python_quiz_attempts
            (user_id, chapter_number, score, total_questions, passed)
            VALUES (?, ?, ?, 5, ?)
            """,
            (
                session["user_id"],
                chapter_number,
                score,
                passed
            )
        )

        db.commit()

        if passed:

            flash(
                f"Congratulations! Quiz {chapter_number} passed "
                f"with {score}/5. The next chapter is unlocked!",
                "success"
            )

        else:

            flash(
                f"You scored {score}/5. You need 4/5 to pass. Try again!",
                "error"
            )

        return redirect(url_for("python_course"))

    return render_template(
        "python_quiz.html",
        questions=questions,
        chapter_number=chapter_number,
        chapter_title=PYTHON_CHAPTERS[chapter_number - 1]["title"]
    )

# ==========================================
# FINAL EXAM
# ==========================================

@app.route(
    "/course/python/final-exam",
    methods=["GET", "POST"]
)
@login_required
def python_final_exam():

    if not is_python_enrolled():

        flash("Please enroll in Python Programming first.", "info")
        return redirect(url_for("courses"))

    if not all_python_quizzes_passed():

        flash(
            "Pass all 11 chapter quizzes before attempting the final exam.",
            "error"
        )

        return redirect(url_for("python_course"))

    previous_pass = get_db().execute(
        """
        SELECT id
        FROM python_final_exam_attempts
        WHERE user_id = ? AND passed = 1
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    if previous_pass:

        return redirect(url_for("python_certificate"))

    questions = get_final_exam_questions()

    if request.method == "POST":

        answers = []

        for number in range(1, 51):

            answer = request.form.get(f"q{number}")

            if answer not in ["A", "B", "C", "D"]:

                flash("Please answer all 50 questions.", "error")
                return redirect(url_for("python_final_exam"))

            answers.append(answer)

        score = sum(
            answers[index] == questions[index]["answer"]
            for index in range(50)
        )

        passed = int(score >= 40)

        db = get_db()

        db.execute(
            """
            INSERT INTO python_final_exam_attempts
            (user_id, score, total_questions, passed)
            VALUES (?, ?, 50, ?)
            """,
            (session["user_id"], score, passed)
        )

        db.commit()

        if passed:

            certificate = get_certificate()

            if not certificate:

                certificate_id = (
                    "SHA-PY-" + uuid.uuid4().hex[:10].upper()
                )

                db.execute(
                    """
                    INSERT INTO certificates
                    (user_id, certificate_id)
                    VALUES (?, ?)
                    """,
                    (session["user_id"], certificate_id)
                )

                db.commit()

            flash(
                f"Congratulations! You passed with {score}/50. "
                "Your certificate is ready!",
                "success"
            )

            return redirect(url_for("python_certificate"))

        flash(
            f"You scored {score}/50. You need at least 40/50 to pass. "
            "You can try again.",
            "error"
        )

        return redirect(url_for("python_final_exam"))

    return render_template(
        "final_exam.html",
        questions=questions,
        user_name=session.get("user_name", "Student")
    )

# ==========================================
# CERTIFICATE PAGE
# ==========================================

@app.route("/course/python/certificate")
@login_required
def python_certificate():

    if not is_python_enrolled() or not all_python_quizzes_passed():

        flash("Complete your Python course first.", "error")
        return redirect(url_for("python_course"))

    certificate = get_certificate()

    if not certificate:

        flash("Pass the final exam to receive your certificate.", "info")
        return redirect(url_for("python_final_exam"))

    return render_template(
        "certificate.html",
        user_name=session.get("user_name", "Student"),
        certificate=certificate
    )

# ==========================================
# DOWNLOAD CERTIFICATE PDF
# ==========================================

@app.route("/course/python/certificate/download")
@login_required
def download_python_certificate():

    if not is_python_enrolled() or not all_python_quizzes_passed():
        flash("Complete your Python course first.", "error")
        return redirect(url_for("python_course"))

    certificate = get_certificate()

    if not certificate:
        flash("Pass the final exam to download your certificate.", "info")
        return redirect(url_for("python_final_exam"))

    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
        from reportlab.lib.utils import ImageReader
    except ImportError:
        flash("PDF library missing. Install reportlab first.", "error")
        return redirect(url_for("python_certificate"))

    # Keep this image in:
    # static/certificates/certificate_template.png
    template_path = os.path.join(
        BASE_DIR, "static", "certificates", "certificate_template.png"
    )

    if not os.path.isfile(template_path):
        flash(
            "Certificate design image is missing. Please add "
            "static/certificates/certificate_template.png.",
            "error"
        )
        return redirect(url_for("python_certificate"))

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Use the finalized certificate artwork as the full-page background.
    pdf.drawImage(
        ImageReader(template_path),
        0, 0,
        width=page_width,
        height=page_height,
        preserveAspectRatio=False,
        mask="auto"
    )

    # Dynamic student and certificate details.
    student_name = session.get("user_name", "Student").strip()
    certificate_id = certificate["certificate_id"]
    issued_date = str(certificate["issued_at"])[:10]

    # Coordinates are aligned to the blank name, ID and date areas
    # in the approved 1536 x 1087 certificate template.
    scale_x = page_width / 1536
    scale_y = page_height / 1087

    # Student name: centered above the long gold name line.
    name_font_size = 30
    pdf.setFillColor(HexColor("#B8860B"))
    pdf.setFont("Times-BoldItalic", name_font_size)

    max_name_width = 760 * scale_x
    while (
        pdf.stringWidth(student_name, "Times-BoldItalic", name_font_size)
        > max_name_width
        and name_font_size > 16
    ):
        name_font_size -= 1
        pdf.setFont("Times-BoldItalic", name_font_size)

    pdf.drawCentredString(
        page_width / 2,
        page_height - (510 * scale_y),
        student_name
    )

    # Certificate ID: positioned on the left footer's blank writing line.
    # The approved artwork contains the "Certificate ID :" label.
    pdf.setFillColor(HexColor("#0B2F27"))
    pdf.setFont("Times-Bold", 13)
    pdf.drawCentredString(
        390 * scale_x,
        page_height - (895 * scale_y),
        certificate_id
    )

    # Issue date: positioned on the right footer's blank writing line.
    # The approved artwork contains the "Issue Date :" label.
    pdf.setFont("Times-Bold", 13)
    pdf.drawCentredString(
        1225 * scale_x,
        page_height - (895 * scale_y),
        issued_date
    )

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Shreshwat_Python_Certificate.pdf",
        mimetype="application/pdf"
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "info")

    return redirect(url_for("index"))

# ==========================================
# GLOBAL TEMPLATE VARIABLES
# ==========================================

@app.context_processor
def inject_user():

    return {
        "logged_in": "user_id" in session,
        "current_user": session.get("user_name")
    }

# ==========================================
# INITIALIZE DATABASE
# ==========================================

init_db()

# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)