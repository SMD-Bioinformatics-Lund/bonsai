"""Declaration of views for samples"""
from flask import Blueprint, current_app, render_template, request
from app.mimer import cgmlst_cluster_samples, TokenObject
from flask_login import login_required, current_user

cluster_bp = Blueprint(
    "cluster", __name__, template_folder="templates", static_folder="static"
)

# @cluster_bp.route("/cluster/", methods=['GET', 'POST'])
# @login_required
# def cluster(sample_id):
#     """cluster view."""
#     token = TokenObject(**current_user.get_id())

#     if request.method == 'POST':
#         samples = request.body['samples']
#         print(samples)
#         cgmlst_cluster_samples(token, samples=samples)
#     return render_template("cluster.html", sample_id=sample_id)

@cluster_bp.route("/cluster/cgmlst", methods=['GET', 'POST'])
@login_required
def cgmlst():
    """cgmlst view."""
    token = TokenObject(**current_user.get_id())

    if request.method == 'POST':
        samples = request.form.getlist('samples')
        #nwk = cgmlst_cluster_samples(token, samples=samples)
    return render_template("cluster.html", samples=samples)