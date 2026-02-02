from app import app, db, Site

with app.app_context():
    sites = Site.query.all()
    print(f"Total sites: {len(sites)}")
    for site in sites:
        print(f"ID: {site.id}, Name: {site.name}, Status: '{site.status}', FailureTime: {site.first_failure_time}, Error: {site.error_message}")
