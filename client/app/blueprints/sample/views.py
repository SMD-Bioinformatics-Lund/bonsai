"""Declaration of views for samples"""
from flask import Blueprint, current_app, render_template
from flask_login import login_required

samples_bp = Blueprint("samples", __name__, template_folder="templates", static_folder="static")

@samples_bp.route('/samples')
@login_required
def samples():
    """Samples view."""
    return render_template("samples.html")