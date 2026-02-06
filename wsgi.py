from app import create_app, init_db

app = create_app()

# Initialize DB (Safe to run multiple times, checks existence)
# In production with multiple workers, this might run multiple times if not careful,
# but our init_db logic checks existence first.
# A better approach for Gunicorn is running this as a separate command in entrypoint,
# but keeping it here maintains current behavior for simplicity unless race conditions arise.
with app.app_context():
    init_db(app)

if __name__ == "__main__":
    app.run()
