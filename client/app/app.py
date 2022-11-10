"""Code for setting up the flask app."""
from flask import Flask, current_app
from .blueprints import public, login, groups, sample, cluster
from .extensions import login_manager
from dateutil.parser import parse
from jsonpath2.path import Path as JsonPath
from .models import Severity, VirulenceTag, TagType, Tag, TAG_LIST
from itertools import chain
from collections import defaultdict


def create_app():
    """Flask app factory function."""

    app = Flask(__name__)
    # load default config
    app.config.from_pyfile("config.py")
    # setup secret key
    app.secret_key = app.config["SECRET_KEY"]

    # initialize flask extensions
    login_manager.init_app(app)

    # import jinja2 extensions
    app.jinja_env.add_extension("jinja2.ext.do")
    app.jinja_env.globals.update(zip=zip)

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

    @app.template_filter()
    def get_all_phenotypes(res):
        susceptible = res["result"]["phenotypes"]["susceptible"]
        resistant = res["result"]["phenotypes"]["resistant"]
        all_phenotypes = ", ".join(chain(susceptible, resistant))
        return f"All phenotypes: {all_phenotypes}"

    @app.template_filter()
    def camelcase_to_text(text):
        return text.replace("_", " ")

    @app.template_filter()
    def cgmlst_count_called(alleles):
        return sum(1 for allele in alleles.values() if allele is not None)

    @app.template_filter()
    def cgmlst_count_missing(alleles):
        return sum(1 for allele in alleles.values() if allele is None)

    @app.template_filter()
    def groupby_antib_class(antibiotics):
        # todo lookup antibiotic classes in database
        antibiotic_classes = {
            "tobramycin": "aminoglycoside",
            "gentamicin": "aminoglycoside",
            "ampicillin+clavulanic acid": "beta-lactam",
            "amoxicillin": "beta-lactam"
        }
        result = defaultdict(list)
        for antib in antibiotics:
            if antib in antibiotic_classes:
                result[antibiotic_classes[antib]].append(antib)
        return result

    @app.template_filter()
    def fmt_number(num):
        """Format number by adding a thousand separator"""
        if isinstance(num, (int, float)):
            num = "{:,}".format(num)
        return num