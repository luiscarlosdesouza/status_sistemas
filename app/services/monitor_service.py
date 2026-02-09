import requests
from datetime import datetime
from ..extensions import db
from ..models import Site, SiteHistory, GlobalSettings
from .email_service import send_alert_email, send_recovery_email

def check_sites(app, force=False):
    # print("Tick...") 
    with app.app_context():
        settings = GlobalSettings.query.first()
        if not settings:
            return

        # Determine current interval (Weekday vs Weekend)
        # Weekday: 0-4 (Mon-Fri), Weekend: 5-6 (Sat-Sun)
        is_weekend = datetime.now().weekday() >= 5
        current_interval_minutes = settings.interval_weekend if is_weekend else settings.interval_weekday
        threshold_seconds = settings.alert_threshold * 60

        sites = Site.query.all()
        for site in sites:
            # Check if it is time to check this site (unless forced)
            if not force and site.last_checked:
                time_since_check = datetime.now() - site.last_checked
                if time_since_check.total_seconds() < (current_interval_minutes * 60):
                    continue # Skip, not time yet

            # --- Perform Check ---
            print(f"Checking {site.name}...")
            previous_status = site.status
            try:
                response = requests.get(site.url, timeout=30)
                is_success = False
                
                if response.status_code == 200:
                    if site.expected_text:
                        if site.expected_text in response.text:
                            is_success = True
                        else:
                            is_success = False
                            error_msg = f"Texto esperado '{site.expected_text}' não encontrado."
                    else:
                        is_success = True
                else:
                    is_success = False
                    error_msg = f"Status Code: {response.status_code}"

                if is_success:
                    # Success State
                    if site.status == 'offline':
                        send_recovery_email(site, settings)
                        
                        # Close History
                        history_entry = SiteHistory.query.filter_by(site_id=site.id, end_time=None).first()
                        if history_entry:
                            history_entry.end_time = datetime.now()
                    
                    site.status = 'online'
                    site.first_failure_time = None
                    site.error_message = None
                else:
                    # Failure State
                    site.error_message = error_msg
                    
                    if site.first_failure_time is None:
                        # First failure detected
                        site.first_failure_time = datetime.now()
                        site.status = 'warning'
                    else:
                        # Successive failure
                        time_diff = datetime.now() - site.first_failure_time
                        if time_diff.total_seconds() >= threshold_seconds:
                            site.status = 'offline'
                            
                            # Send Alert only if transitioning to offline for the first time
                            if previous_status != 'offline':
                                send_alert_email(site, settings)
                                
                                # Open History
                                new_history = SiteHistory(site_id=site.id, status='offline', start_time=datetime.now(), error_message=site.error_message)
                                db.session.add(new_history)
                        else:
                            site.status = 'warning'

            except Exception as e:
                # Exception Handling
                site.error_message = f"Connection Error: {str(e)}"
                if site.first_failure_time is None:
                    site.first_failure_time = datetime.now()
                    site.status = 'warning'
                else:
                    time_diff = datetime.now() - site.first_failure_time
                    if time_diff.total_seconds() >= threshold_seconds:
                        previous_status = site.status
                        site.status = 'offline'
                        if previous_status != 'offline':
                            send_alert_email(site, settings)
                            new_history = SiteHistory(site_id=site.id, status='offline', start_time=datetime.now(), error_message=site.error_message)
                            db.session.add(new_history)
                    else:
                        site.status = 'warning'
            
            site.last_checked = datetime.now()
            
        db.session.commit()
