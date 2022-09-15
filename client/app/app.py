"""Code for setting up the flask app."""
from flask import Flask, current_app
from .blueprints import public, login, groups, sample, cluster
from .extensions import login_manager
from dateutil.parser import parse
from jsonpath2.path import Path as JsonPath
from .models import Severity, VirulenceTag, TagType, Tag, TAG_LIST


def create_app():
    """Flask app factory function."""

    app = Flask(__name__)
    # load default config
    app.config.from_pyfile("config.py")
    # setup secret key
    app.secret_key = app.config["SECRET_KEY"]

    # initialize flask extensions
    login_manager.init_app(app)

    # configure pages etc
    register_blueprints(app)
    register_filters(app)

    @app.template_filter("strftime")
    def _jinja2_filter_datetime(date, fmt=None):
        date = parse(date)
        native = date.replace(tzinfo=None)
        format = "%b %d, %Y"
        return native.strftime(format)

    return app


def register_blueprints(app):
    """Register flask blueprints."""
    app.register_blueprint(public.public_bp)
    app.register_blueprint(login.login_bp)
    app.register_blueprint(sample.samples_bp)
    app.register_blueprint(groups.groups_bp)
    app.register_blueprint(cluster.cluster_bp)


def register_filters(app):
    """Register jinja2 filter functions."""

    @app.template_filter()
    def json_path(json_blob, json_path):
        """Get data from json blob with JSONpath."""
        jsonpath_expr = JsonPath.parse_str(json_path)
        for match in jsonpath_expr.match(json_blob):
            return match.current_value

    @app.template_filter()
    def has_arg(amr_result, arg_name: str) -> bool:
        """Check if an antimicrobial resistance gene with NAME has been predicted."""
        # next(JsonPath.parse_str("$.typingResult[?(@.type='mlst')]").match(json_blob)).current_value
        for gene in amr_result["genes"]:
            if gene["name"] == arg_name:
                return True
        return False

    @app.template_filter()
    def is_pvl_pos(vir_result) -> TAG_LIST:
        """Check if sample is PVL positive."""
        has_lukS = any(gene["name"] == "lukS-PV" for gene in vir_result["genes"])
        has_lukF = any(gene["name"] == "lukF-PV" for gene in vir_result["genes"])

        # get the tags
        if has_lukF and has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_POS,
                description="",
                severity=Severity.DANGER,
            )
        elif any([has_lukF and not has_lukS, has_lukS and not has_lukF]):
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_LUKF_POS
                if has_lukF
                else VirulenceTag.PVL_LUKS_POS,
                description="",
                severity=Severity.WARNING,
            )
        elif not has_lukF and not has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_NEG,
                description="",
                severity=Severity.PASSED,
            )
        return tag
