"""Code for setting up the flask app."""
from collections import defaultdict
from itertools import chain, zip_longest

from flask import Flask, current_app

from dateutil.parser import parse
from jsonpath2.path import Path as JsonPath

from .blueprints import api, cluster, groups, login, public, sample
from .extensions import login_manager
from .models import TAG_LIST, Severity, Tag, TagType, VirulenceTag


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
    app.jinja_env.globals.update(zip_longest=zip_longest)

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
    app.register_blueprint(api.api_bp)


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

    @app.template_filter("strftime")
    def _jinja2_filter_datetime(date, fmt=None):
        date = dateutil.parser.parse(date)
        native = date.replace(tzinfo=None)
        format = "%b %d, %Y"
        return native.strftime(format)

    @app.template_filter()
    def cgmlst_count_called(alleles):
        return sum(1 for allele in alleles.values() if allele is not None)

    @app.template_filter()
    def cgmlst_count_missing(alleles):
        return sum(1 for allele in alleles.values() if allele is None)

    @app.template_filter()
    def nt_to_aa(nt_seq):
        """Translate nucleotide sequence to aa sequence"""
        TABLE = {
            "TTT": "F",
            "TTC": "F",
            "TTA": "L",
            "TTG": "L",
            "TCT": "S",
            "TCC": "S",
            "TCA": "S",
            "TCG": "S",
            "TAT": "Y",
            "TAC": "Y",  # noqa: E241
            "TGT": "C",
            "TGC": "C",
            "TGG": "W",  # noqa: E241
            "CTT": "L",
            "CTC": "L",
            "CTA": "L",
            "CTG": "L",
            "CCT": "P",
            "CCC": "P",
            "CCA": "P",
            "CCG": "P",
            "CAT": "H",
            "CAC": "H",
            "CAA": "Q",
            "CAG": "Q",
            "CGT": "R",
            "CGC": "R",
            "CGA": "R",
            "CGG": "R",
            "ATT": "I",
            "ATC": "I",
            "ATA": "I",
            "ATG": "M",
            "ACT": "T",
            "ACC": "T",
            "ACA": "T",
            "ACG": "T",
            "AAT": "N",
            "AAC": "N",
            "AAA": "K",
            "AAG": "K",
            "AGT": "S",
            "AGC": "S",
            "AGA": "R",
            "AGG": "R",
            "GTT": "V",
            "GTC": "V",
            "GTA": "V",
            "GTG": "V",
            "GCT": "A",
            "GCC": "A",
            "GCA": "A",
            "GCG": "A",
            "GAT": "D",
            "GAC": "D",
            "GAA": "E",
            "GAG": "E",
            "GGT": "G",
            "GGC": "G",
            "GGA": "G",
            "GGG": "G",
        }
        stop_codons = (["TAA", "TAG", "TGA"],)
        start_codons = (["TTG", "CTG", "ATT", "ATC", "ATA", "ATG", "GTG"],)
        aa_seq = ""
        for pos in range(0, len(nt_seq), 3):
            codon = nt_seq[pos : pos + 3].upper()
            if codon in start_codons:
                aa_seq += "START"
            elif codon in stop_codons:
                aa_seq += "STOP"
            else:
                aa_seq += TABLE[codon]
        return aa_seq

    @app.template_filter()
    def groupby_antib_class(antibiotics):
        # todo lookup antibiotic classes in database
        antibiotic_class_lookup = {
            antib.lower(): k
            for k, v in current_app.config.get("ANTIBIOTIC_CLASSES", {}).items()
            for antib in v
        }
        result = defaultdict(list)
        for antib in antibiotics:
            antib_class = antibiotic_class_lookup.get(antib, "unknown")
            result[antib_class].append(antib)
        result = {k: result[k] for k in sorted(result)}
        return result

    @app.template_filter()
    def fmt_number(num, sig_digits=None):
        """Format number by adding a thousand separator

        Has option to round values to X signifiacnt digits."""
        if isinstance(num, (int, float)):
            if sig_digits is not None:
                num = round(num, sig_digits)
            num = "{:,}".format(num)
        return num

    @app.template_filter()
    def fmt_null_values(value):
        """Replace null values with -."""
        if value is None:
            value = "–"
        return value

    @app.template_filter()
    def has_same_analysis_profile(samples):
        """Check if all samples from session cache have the same analysis profile."""
        profiles = [sample["analysis_profile"] for sample in samples]
        return len(set(profiles)) == 1
