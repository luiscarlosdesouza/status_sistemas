from app import create_app, init_db

app = create_app()

# Initialize DB removed to avoid Gunicorn worker race conditions on SQLite
# DB should be initialized via a separate command if needed (e.g. flask init-db)
# with app.app_context():
#    init_db(app)

if __name__ == "__main__":
    app.run()
