from app import create_app, init_db

app = create_app()

if __name__ == "__main__":
    print("Initializing database...")
    init_db(app)
    print("Database initialized successfully!")
