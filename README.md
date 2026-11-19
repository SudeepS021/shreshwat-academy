# Shreshwat Academy — Starter Website

A starter Flask website for Shreshwat Academy with:
- Professional homepage
- Courses overview
- Student registration and login
- SQLite database
- Password hashing
- Basic student dashboard

## Run in VS Code

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Open Terminal > New Terminal.
4. Create a virtual environment:

   Windows:
   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   ```

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

6. Run the website:
   ```bash
   python app.py
   ```

7. Open http://127.0.0.1:5000 in your browser.

The SQLite database (`shreshwat.db`) is created automatically.

## Before public deployment
- Set a strong random `SECRET_KEY` environment variable.
- Turn off Flask debug mode.
- Add CSRF protection, email verification, password reset, rate limiting, and production-grade database/hosting configuration.
- The course/video progress, quizzes, exams, certificates, QR verification, payments for optional notes, and admin panel are not implemented yet; they are planned next stages.
