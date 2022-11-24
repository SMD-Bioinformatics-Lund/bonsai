"""Declaration of views for samples"""
from flask import Blueprint, current_app, render_template, redirect, session, request
from app.mimer import cgmlst_cluster_samples, get_sample_by_id, post_comment_to_sample, TokenObject
from flask_login import login_required, current_user

samples_bp = Blueprint(
    "samples", __name__, template_folder="templates", static_folder="static", static_url_path="/samples/static"
)


@samples_bp.route("/samples")
@login_required
def samples():
    """Samples view."""
    return render_template("samples.html")


@samples_bp.route("/samples/<sample_id>")
@login_required
def sample(sample_id):
    """Samples view."""
    token = TokenObject(**current_user.get_id())
    sample = get_sample_by_id(token, sample_id=sample_id)
    return render_template("sample.html", sample=sample)


@samples_bp.route("/samples/<sample_id>/comment", methods=["POST"])
@login_required
def add_comment(sample_id):
    """Post sample."""
    token = TokenObject(**current_user.get_id())
    # post comment
    data = request.form["comment"]
    # todo validate data
    try:
        resp = post_comment_to_sample(token, sample_id=sample_id, user_name=current_user.username, comment=data)
    except:
        flash(resp.text)
    finally:
        return redirect(session["url"])


@samples_bp.route("/samples/<sample_id>/resistance_report")
@login_required
def resistance_report(sample_id):
    """Samples view."""
    token = TokenObject(**current_user.get_id())
    sample = get_sample_by_id(token, sample_id=sample_id)
    return render_template("resistance_report.html", sample=sample)


@samples_bp.route("/cluster/", methods=['GET', 'POST'])
@login_required
def cluster(sample_id):
    """Samples view."""
    token = TokenObject(**current_user.get_id())

    if request.method == 'POST':
        samples = request.body['samples']
        cgmlst_cluster_samples(token, samples=samples)
    return render_template("sample.html", sample_id=sample_id)
