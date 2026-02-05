from app import create_app, init_db

app = create_app()

if __name__ == '__main__':
    # Initialize DB data on startup (Seeding)
    # Note: Structure should be handled by 'flask db upgrade' ideally
    # But for ease of use we call init_db to seed Admin/Settings
    init_db(app)
    app.run(host='0.0.0.0', port=5000, debug=True)
