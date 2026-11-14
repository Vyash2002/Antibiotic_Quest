"""Antibiotic Quest - Flask application factory."""
import os

from flask import Flask, render_template

from . import admin, api, db


def load_env_file(path):
    """Minimal .env reader (KEY=VALUE lines) so no extra package is needed."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def create_app(test_config=None):
    load_env_file(os.path.join(db.ROOT, ".env"))
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("AQ_DATABASE", os.path.join(db.ROOT, "db", "antibiotic_quest.db")),
        ADMIN_TOKEN=os.environ.get("ADMIN_TOKEN", "change-me"),
        GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY", ""),
        GEMINI_MODEL=os.environ.get("GEMINI_MODEL", "gemini-flash-latest"),
        JSON_AS_ASCII=False,
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )
    if test_config:
        app.config.update(test_config)
    app.json.ensure_ascii = False

    db.ensure_database(app.config["DATABASE"])
    db.init_app(app)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.after_request
    def no_cache_api(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        return resp

    return app
