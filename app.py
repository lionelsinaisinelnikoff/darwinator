#!/usr/bin/env python3
"""
DARWINATOR
The Innovation Tournament Platform
Inspired by the research of Karan Girotra, Christian Terwiesch & Karl T. Ulrich

Core insight: Value is driven by the exceptional few.
The hybrid process (individuals generate alone → group evaluates) reliably surfaces
better best ideas than pure team brainstorming.

Built for MBA and executive education.
"""

import os
import sqlite3
import random
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, g,
    send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "darwinator-hybrid-process-2026-sharp")
app.config["DATABASE"] = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "darwinator.db")
)

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    c = db.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'student' CHECK(role IN ('student','admin')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        current_round INTEGER DEFAULT 1,
        round1_open INTEGER DEFAULT 1,
        round2_open INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        round INTEGER DEFAULT 1 CHECK(round IN (1,2)),
        name TEXT NOT NULL,
        description TEXT,
        slides_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idea_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 0 AND 10),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(idea_id, user_id),
        FOREIGN KEY (idea_id) REFERENCES ideas(id),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    db.commit()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed_demo(db)

def seed_demo(db):
    c = db.cursor()
    c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
              ("admin", generate_password_hash("stern2026")))
    students = ["rafiki_mba", "elisa_innovate", "lionel_strategist", "cintia_esg", "alex_vc", "sara_product", "omar_energy"]
    student_ids = []
    for s in students:
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'student')",
                  (s, generate_password_hash("demo2026")))
        student_ids.append(c.lastrowid)
    c.execute("""INSERT INTO tournaments (code, name, description, current_round, round1_open, round2_open)
                 VALUES (?, ?, ?, 1, 1, 0)""", (
        "NSAD-TPMI-F25-R1",
        "Tech Product Ideation — NYU Stern Abu Dhabi",
        "Hybrid innovation tournament. Individuals generate independently, then the group evaluates. Focus on the quality of the best idea."))
    tid = c.lastrowid
    samples = [
        ("AeroGuard AI", "Real-time risk intelligence for hydrogen aviation fleets combining satellite data and edge ML."),
        ("SolarMate Modular", "AI-optimized modular solar + storage ecosystem for UAE villas with community sharing."),
        ("VitaTrack Patch", "Continuous non-invasive monitoring for vitiligo progression with flare prediction."),
        ("EduSpark", "Spotify-for-academia: open-access research with engagement-based author payouts."),
        ("GreenH2 Microhub", "Decentralized green hydrogen micro-hubs for last-mile aviation and heavy transport."),
        ("One XR ISR", "Long-endurance dual-use hydrogen aircraft variant for 24h ISR with 1-ton payload."),
        ("Pulse Defense", "C-UAS and soft-kill systems intelligence platform for regional airspace."),
    ]
    for i, (name, desc) in enumerate(samples):
        uid = student_ids[i % len(student_ids)]
        c.execute("INSERT INTO ideas (tournament_id, user_id, round, name, description) VALUES (?, ?, 1, ?, ?)",
                  (tid, uid, name, desc))
    idea_ids = [r[0] for r in c.execute("SELECT id FROM ideas WHERE round=1").fetchall()]
    for iid in idea_ids:
        for sid in student_ids[:4]:
            rating = random.randint(5, 9)
            c.execute("INSERT OR IGNORE INTO evaluations (idea_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
                      (iid, sid, rating, "Promising direction for the region." if rating >= 7 else "Needs clearer differentiation."))
    db.commit()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

def get_tournament():
    return get_db().execute("SELECT * FROM tournaments LIMIT 1").fetchone()

def get_user_ideas(user_id, tournament_id, round_num=1):
    return get_db().execute("""
        SELECT i.*, COUNT(e.id) as num_ratings, COALESCE(AVG(e.rating), 0) as avg_rating
        FROM ideas i LEFT JOIN evaluations e ON i.id = e.idea_id
        WHERE i.user_id = ? AND i.tournament_id = ? AND i.round = ?
        GROUP BY i.id ORDER BY avg_rating DESC, i.created_at DESC
    """, (user_id, tournament_id, round_num)).fetchall()

def get_unrated_ideas(user_id, tournament_id, round_num=1, limit=6):
    return get_db().execute("""
        SELECT i.* FROM ideas i
        WHERE i.tournament_id = ? AND i.round = ?
          AND i.id NOT IN (SELECT idea_id FROM evaluations WHERE user_id = ?)
        ORDER BY RANDOM() LIMIT ?
    """, (tournament_id, round_num, user_id, limit)).fetchall()

def compute_rank(idea_id, tournament_id, round_num=1):
    rows = get_db().execute("""
        SELECT i.id, COALESCE(AVG(e.rating), 0) as avg_r
        FROM ideas i LEFT JOIN evaluations e ON i.id = e.idea_id
        WHERE i.tournament_id = ? AND i.round = ?
        GROUP BY i.id ORDER BY avg_r DESC
    """, (tournament_id, round_num)).fetchall()
    for rank, r in enumerate(rows, 1):
        if r["id"] == idea_id:
            return rank
    return None

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome, {username}.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    tournament = get_tournament()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        code = request.form.get("tournament_code", "").strip().upper()
        if not tournament or code != tournament["code"]:
            flash("Invalid tournament code.", "danger")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "warning")
            return redirect(url_for("register"))
        try:
            get_db().execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'student')",
                            (username, generate_password_hash(password)))
            get_db().commit()
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "danger")
    return render_template("register.html", tournament=tournament)

@app.route("/logout")
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    tournament = get_tournament()
    user_id = session["user_id"]
    db = get_db()
    my_ideas_r1 = get_user_ideas(user_id, tournament["id"], 1)
    my_ratings = db.execute("SELECT COUNT(*) FROM evaluations WHERE user_id = ?", (user_id,)).fetchone()[0]
    total_r1 = db.execute("SELECT COUNT(*) FROM ideas WHERE tournament_id = ? AND round = 1", (tournament["id"],)).fetchone()[0]
    unrated = len(get_unrated_ideas(user_id, tournament["id"], 1, 200))
    round2_ideas = get_user_ideas(user_id, tournament["id"], 2) if tournament["current_round"] >= 2 else []
    return render_template("dashboard.html", tournament=tournament, my_ideas_r1=my_ideas_r1,
                           my_ratings=my_ratings, total_r1=total_r1, unrated=unrated,
                           round2_ideas=round2_ideas, username=session["username"], role=session["role"])

@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    tournament = get_tournament()
    if not tournament["round1_open"]:
        flash("Round 1 submission is closed.", "warning")
        return redirect(url_for("dashboard"))
    user_id = session["user_id"]
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name or not description:
            flash("Name and description are required.", "danger")
            return redirect(url_for("submit"))
        count = db.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ? AND tournament_id = ? AND round = 1",
                           (user_id, tournament["id"])).fetchone()[0]
        if count >= 10:
            flash("Maximum of 10 ideas reached for Round 1.", "warning")
            return redirect(url_for("submit"))
        db.execute("INSERT INTO ideas (tournament_id, user_id, round, name, description) VALUES (?, ?, 1, ?, ?)",
                   (tournament["id"], user_id, name, description))
        db.commit()
        flash(f'Idea “{name}” submitted. Volume + variance increase the chance of an exceptional idea.', "success")
        return redirect(url_for("submit"))
    my_ideas = get_user_ideas(user_id, tournament["id"], 1)
    return render_template("submit.html", tournament=tournament, my_ideas=my_ideas)

@app.route("/evaluate", methods=["GET", "POST"])
@login_required
def evaluate():
    tournament = get_tournament()
    user_id = session["user_id"]
    db = get_db()
    round_num = tournament["current_round"]
    if request.method == "POST":
        rated = 0
        for key in request.form:
            if key.startswith("rating_"):
                try:
                    idea_id = int(key.split("_")[1])
                    rating = int(request.form[key])
                    if 0 <= rating <= 10:
                        comment = request.form.get(f"comment_{idea_id}", "").strip()
                        db.execute("INSERT OR REPLACE INTO evaluations (idea_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
                                   (idea_id, user_id, rating, comment))
                        rated += 1
                except (ValueError, IndexError):
                    pass
        db.commit()
        if rated:
            flash(f"Thank you. You rated {rated} idea(s). Your discernment helps surface the exceptional few.", "success")
        return redirect(url_for("evaluate"))
    unrated = get_unrated_ideas(user_id, tournament["id"], round_num, limit=5)
    my_count = db.execute("""SELECT COUNT(*) FROM evaluations e JOIN ideas i ON e.idea_id = i.id
                            WHERE e.user_id = ? AND i.round = ?""", (user_id, round_num)).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM ideas WHERE tournament_id = ? AND round = ?",
                       (tournament["id"], round_num)).fetchone()[0]
    return render_template("evaluate.html", tournament=tournament, unrated=unrated,
                           my_count=my_count, total=total, round_num=round_num)

@app.route("/reports")
@login_required
def reports():
    tournament = get_tournament()
    my_ideas = get_user_ideas(session["user_id"], tournament["id"], 1)
    enriched = []
    for idea in my_ideas:
        rank = compute_rank(idea["id"], tournament["id"], 1)
        enriched.append({**dict(idea), "global_rank": rank})
    return render_template("reports.html", tournament=tournament, my_ideas=enriched)

@app.route("/round2", methods=["GET", "POST"])
@login_required
def round2():
    tournament = get_tournament()
    if tournament["current_round"] < 2 or not tournament["round2_open"]:
        flash("Round 2 is not open yet.", "warning")
        return redirect(url_for("dashboard"))
    user_id = session["user_id"]
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slides_url = request.form.get("slides_url", "").strip()
        if not name or not slides_url:
            flash("Solution name and presentation URL are required.", "danger")
            return redirect(url_for("round2"))
        existing = db.execute("SELECT id FROM ideas WHERE user_id = ? AND tournament_id = ? AND round = 2",
                              (user_id, tournament["id"])).fetchone()
        if existing:
            flash("You have already advanced one solution.", "info")
            return redirect(url_for("round2"))
        db.execute("INSERT INTO ideas (tournament_id, user_id, round, name, description, slides_url) VALUES (?, ?, 2, ?, ?, ?)",
                   (tournament["id"], user_id, name, "Advanced solution for Round 2.", slides_url))
        db.commit()
        flash("Solution advanced to Round 2.", "success")
        return redirect(url_for("dashboard"))
    my_r1 = get_user_ideas(user_id, tournament["id"], 1)
    return render_template("round2.html", tournament=tournament, my_r1=my_r1)

@app.route("/admin")
@login_required
@admin_required
def admin():
    tournament = get_tournament()
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        "ideas_r1": db.execute("SELECT COUNT(*) FROM ideas WHERE tournament_id=? AND round=1", (tournament["id"],)).fetchone()[0],
        "evaluations": db.execute("SELECT COUNT(*) FROM evaluations e JOIN ideas i ON e.idea_id = i.id WHERE i.tournament_id = ?", (tournament["id"],)).fetchone()[0],
        "avg_rating": db.execute("SELECT COALESCE(AVG(e.rating), 0) FROM evaluations e JOIN ideas i ON e.idea_id = i.id WHERE i.round = 1 AND i.tournament_id = ?", (tournament["id"],)).fetchone()[0],
    }
    top_ideas = db.execute("""
        SELECT i.*, u.username as submitter, COUNT(e.id) as num_ratings, COALESCE(AVG(e.rating), 0) as avg_rating
        FROM ideas i JOIN users u ON i.user_id = u.id LEFT JOIN evaluations e ON i.id = e.idea_id
        WHERE i.tournament_id = ? AND i.round = 1 GROUP BY i.id ORDER BY avg_rating DESC, num_ratings DESC LIMIT 12
    """, (tournament["id"],)).fetchall()
    round2_solutions = []
    if tournament["current_round"] >= 2:
        round2_solutions = db.execute("""
            SELECT i.*, u.username as submitter, COUNT(e.id) as num_ratings, COALESCE(AVG(e.rating), 0) as avg_rating
            FROM ideas i JOIN users u ON i.user_id = u.id LEFT JOIN evaluations e ON i.id = e.idea_id
            WHERE i.tournament_id = ? AND i.round = 2 GROUP BY i.id ORDER BY avg_rating DESC
        """, (tournament["id"],)).fetchall()
    return render_template("admin.html", tournament=tournament, stats=stats, top_ideas=top_ideas, round2_solutions=round2_solutions)

@app.route("/admin/advance", methods=["POST"])
@login_required
@admin_required
def advance_round():
    tournament = get_tournament()
    new_round = int(request.form.get("new_round", 2))
    db = get_db()
    if new_round == 2:
        db.execute("UPDATE tournaments SET current_round=2, round1_open=0, round2_open=1 WHERE id=?", (tournament["id"],))
        flash("Round 1 closed. Round 2 is now open for advanced solutions.", "success")
    elif new_round == 3:
        db.execute("UPDATE tournaments SET current_round=3, round2_open=0 WHERE id=?", (tournament["id"],))
        flash("Round 2 closed. Top ideas are ready for team projects.", "success")
    db.commit()
    return redirect(url_for("admin"))

@app.route("/admin/export")
@login_required
@admin_required
def export():
    try:
        import pandas as pd
    except ImportError:
        flash("pandas is required for export. Install with: pip install pandas", "warning")
        return redirect(url_for("admin"))
    tournament = get_tournament()
    db = get_db()
    df = pd.read_sql_query("""
        SELECT i.id, i.round, i.name, i.description, i.slides_url, u.username as submitter,
               COUNT(e.id) as num_ratings, COALESCE(AVG(e.rating), 0) as avg_rating, i.created_at
        FROM ideas i JOIN users u ON i.user_id = u.id LEFT JOIN evaluations e ON i.id = e.idea_id
        WHERE i.tournament_id = ? GROUP BY i.id ORDER BY i.round, avg_rating DESC
    """, db, params=(tournament["id"],))
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True,
                     download_name=f"darwinator_{tournament['code']}.csv")

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print("\n" + "=" * 62)
    print("  DARWINATOR  —  Innovation Tournament Platform")
    print("  Hybrid process · Quality of the best idea")
    print(f"  →  http://127.0.0.1:{port}")
    print("  Admin: admin / stern2026")
    print("  Students: any seeded username / demo2026")
    print("=" * 62 + "\n")
    app.run(host="0.0.0.0", port=port, debug=True)
