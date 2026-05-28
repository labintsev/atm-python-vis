from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    login_user,
    logout_user,
)
from datetime import datetime, timedelta
import os
import sys
from mssqldb import MSSQLDatabase
from sched_vizual import RadioScheduleVisualizer
from exel_template import ExcelTemplateGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-this")
# Production configuration
app.config["ENV"] = "production"
app.config["DEBUG"] = False
# app.config['PREFERRED_URL_SCHEME'] = 'https'  # Traefik sends X-Forwarded-Proto
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["TRUST_X_FOR_PROXY_COUNT"] = 1  # Trust Traefik headers

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# Simple User class for authentication
class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    # In a real app, you'd query a database. Here we just verify the username exists
    auth_username = os.getenv("AUTH_USERNAME")
    if user_id == auth_username:
        return User(user_id)
    return None


# Global database instance
db = None
db_initialized = False


def init_db():
    """Initialize database connection"""
    global db, db_initialized
    if db_initialized:
        return db is not None

    try:
        db = MSSQLDatabase(
            server="localhost",
            port=1435,
            database=os.getenv("DB_NAME"),
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        db.connect()
        print("Database connected successfully")
        db_initialized = True
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        db_initialized = True
        return False


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        auth_username = os.getenv("AUTH_USERNAME")
        auth_password = os.getenv("AUTH_PASSWORD")

        # Validate credentials
        if username == auth_username and password == auth_password:
            user = User(username)
            login_user(user)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("index"))
        else:
            return render_template(
                "login.html", error="Неверное имя пользователя или пароль"
            )

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Logout route"""
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """Main page with list of radio stations and date picker"""
    try:
        # Initialize database if not already done
        if not db_initialized:
            init_db()

        if db is None:
            return "Ошибка: соединение с базой данных не установлено", 500

        # Get list of radio stations from database
        app.config["radios"] = db.query_radio_points()

        # Default date today
        default_date = datetime.now().strftime("%Y-%m-%d")

        return render_template(
            "index.html", radios=app.config["radios"], default_date=default_date
        )

    except Exception as e:
        print(f"Error in index route: {e}")
        return f"Ошибка при загрузке главной страницы: {str(e)}", 500


@app.route("/schedule")
@login_required
def schedule():
    """Schedule page with Plotly visualization"""
    try:
        # Initialize database if not already done
        if not db_initialized:
            init_db()

        if db is None:
            return "Ошибка: соединение с базой данных не установлено", 500

        # Get parameters from request
        radio_id = request.args.get("radio_id", type=int)
        date_str = request.args.get("date", type=str)

        # Validation
        if radio_id is None:
            return "Ошибка: не указан radio_id", 400

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Validate date format
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return "Ошибка: неверный формат даты (используйте YYYY-MM-DD)", 400

        # Calculate date range (30 days from the selected date)
        date_start = date_str
        date_end = (date_obj + timedelta(days=30)).strftime("%Y-%m-%d")

        # Get data from database
        try:
            radio_names = db.query_radio_points()
            radio_name = (
                radio_names[radio_id]
                if radio_id in radio_names
                else f"RadioID {radio_id}"
            )
            df = db.query_scheds(radio_id, date_start, date_end)
        except Exception as e:
            print(f"Database query error: {e}")
            return f"Ошибка при запросе к базе данных: {str(e)}", 500

        # Check if data is empty
        if df.empty:
            return render_template(
                "schedule.html",
                radio_id=radio_id,
                radio_name=radio_name,
                date=date_str,
                graph_html="<p>Нет данных для выбранной радиостанции и периода</p>",
                has_data=False,
            )
        # Create visualizer and get figure
        try:
            visualizer = RadioScheduleVisualizer(df, radio_id, radio_name)
            fig = visualizer.get_figure()

            # Convert figure to HTML
            graph_html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                # config={"responsive": True}
            )
        except Exception as e:
            print(f"Visualization error: {e}")
            return f"Ошибка при создании визуализации: {str(e)}", 500

        return render_template(
            "schedule.html",
            radio_id=radio_id,
            radio_name=radio_name,
            date=date_str,
            graph_html=graph_html,
            has_data=True,
        )

    except Exception as e:
        print(f"Error in schedule route: {e}")
        return f"Ошибка: {str(e)}", 500


@app.route("/schedule/export")
@login_required
def export_schedule():
    """Export the selected schedule to an Excel file."""
    try:        
        if not db_initialized:
            init_db()

        if db is None:
            return "Ошибка: соединение с базой данных не установлено", 500

        radio_id = request.args.get("radio_id", type=int)
        radio_name = (
            app.config["radios"].get(radio_id, f"RadioID {radio_id}")
            if "radios" in app.config
            else f"RadioID {radio_id}"
        )
        date_str = request.args.get("date", type=str)

        if radio_id is None:
            return "Ошибка: не указан radio_id", 400

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return "Ошибка: неверный формат даты (используйте YYYY-MM-DD)", 400

        date_start = date_str
        date_end = (date_obj + timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            df = db.query_scheds(radio_id, date_start, date_end)
        except Exception as e:
            print(f"Database query error: {e}")
            return f"Ошибка при запросе к базе данных: {str(e)}", 500

        if df.empty:
            return "Нет данных для выбранной радиостанции и периода", 404

        output_file = f"data/МП_{radio_name}_{date_str}.xlsx"
        generator = ExcelTemplateGenerator(df, output_path=output_file)
        generator.generate()

        return send_file(output_file, as_attachment=True)

    except Exception as e:
        print(f"Error in export_schedule route: {e}")
        return f"Ошибка: {str(e)}", 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return "Страница не найдена", 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return "Внутренняя ошибка сервера", 500


if __name__ == "__main__":
    # Initialize database
    if init_db():
        app.run(debug=True, host="localhost", port=5006)
    else:
        print("Failed to initialize database. Exiting.")
        sys.exit(1)
