from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Site, SiteHistory

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    sites = Site.query.all()
    return render_template('index.html', sites=sites)

@main_bp.route('/reports')
@login_required
def reports():
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
    
    # Fetch offline events sorted by start_time desc
    history = SiteHistory.query.order_by(SiteHistory.start_time.desc()).all()
    
    # Calculate duration for display
    enriched_history = []
    for h in history:
        duration = "Em andamento"
        if h.end_time:
            delta = h.end_time - h.start_time
            # Format duration nicely
            minutes, seconds = divmod(delta.total_seconds(), 60)
            hours, minutes = divmod(minutes, 60)
            duration = f"{int(hours)}h {int(minutes)}m"
            
        enriched_history.append({
            'site_name': h.site.name,
            'url': h.site.url,
            'status': h.status,
            'start_time': h.start_time,
            'end_time': h.end_time,
            'duration': duration,
            'error': h.error_message
        })
            
    return render_template('reports.html', history=enriched_history)
