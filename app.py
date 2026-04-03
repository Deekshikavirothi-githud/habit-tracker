from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mysecretkey123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------- MODELS ----------
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'))
    date = db.Column(db.String(20))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- CREATE DB ----------
with app.app_context():
    db.create_all()

# ---------- ROUTES ----------

@app.route("/")
@login_required
def index():
    habits = Habit.query.all()

    habit_data = []
    for h in habits:
        habit_data.append({
            "id": h.id,
            "name": h.name,
            "streak": get_streak(h.id),
            "week": get_last_7_days(h.id)
        })

    return render_template("index.html", habits=habit_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        hashed_password = generate_password_hash(request.form.get("password"))

        new_user = User(
            username=request.form.get("username"),
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/done/<int:id>")
@login_required
def done(id):
    today = str(date.today())

    existing = HabitLog.query.filter_by(habit_id=id, date=today).first()

    if not existing:
        db.session.add(HabitLog(habit_id=id, date=today))
        db.session.commit()

    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
@login_required
def delete(id):
    HabitLog.query.filter_by(habit_id=id).delete()

    habit = Habit.query.get(id)
    db.session.delete(habit)
    db.session.commit()

    return redirect(url_for("index"))


@app.route("/users")
def users():
    return str(User.query.all())


@app.route("/test")
def test():
    return str(current_user.is_authenticated)
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_habit():
    if request.method == "POST":
        habit_name = request.form.get("name")

        new_habit = Habit(name=habit_name)
        db.session.add(new_habit)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("add_habit.html")

# ---------- FUNCTIONS ----------

def get_streak(habit_id):
    logs = HabitLog.query.filter_by(habit_id=habit_id).all()
    dates = sorted([date.fromisoformat(log.date) for log in logs], reverse=True)

    streak = 0
    today = date.today()

    for d in dates:
        if d == today:
            streak += 1
            today = today - timedelta(days=1)
        else:
            break

    return streak


def get_last_7_days(habit_id):
    today = date.today()
    days = []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days.append({
            "date": d,
            "done": HabitLog.query.filter_by(
                habit_id=habit_id,
                date=str(d)
            ).first() is not None
        })

    return days

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()