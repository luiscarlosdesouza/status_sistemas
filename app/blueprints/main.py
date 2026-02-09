from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Site, SiteHistory

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    sites = Site.query.order_by(Site.name).all()
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
            'id': h.id,
            'site_name': h.site.name if h.site else (h.site_name or 'Site Desconhecido'),
            'url': h.site.url if h.site else '',
            'status': h.status,
            'start_time': h.start_time,
            'end_time': h.end_time,
            'duration': duration,
            'error': h.error_message
        })
            
    return render_template('reports.html', history=enriched_history)

@main_bp.route('/reports/pdf')
@login_required
def export_pdf():
    if current_user.role not in ['admin', 'operator']:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
    
    from datetime import datetime
    
    # Fetch history (same logic)
    history = SiteHistory.query.order_by(SiteHistory.start_time.desc()).all()
    
    enriched_history = []
    for h in history:
        duration = "Em andamento"
        if h.end_time:
            delta = h.end_time - h.start_time
            minutes, seconds = divmod(delta.total_seconds(), 60)
            hours, minutes = divmod(minutes, 60)
            duration = f"{int(hours)}h {int(minutes)}m"
            
        enriched_history.append({
            'site_name': h.site.name if h.site else (h.site_name or 'Site Desconhecido'),
            'url': h.site.url if h.site else '',
            'status': h.status,
            'start_time': h.start_time,
            'end_time': h.end_time,
            'duration': duration,
            'error': h.error_message
        })
    
    html = render_template('reports_pdf.html', history=enriched_history, generation_time=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Generate PDF
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        
        from flask import make_response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=relatorio_falhas.pdf'
        return response
    except ImportError:
        flash('Erro: Biblioteca de PDF não instalada no servidor.', 'danger')
        return redirect(url_for('main.reports'))
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('main.reports'))
