from pathlib import Path

import jinja2

from app.config import get_settings
from app.models.deployment import Deployment
from app.models.disk_layout import DiskLayout
from app.models.template import DeploymentTemplate

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).parent.parent / "templates" / "xml"),
    # select_autoescape(["xml"]) looks for a ".xml" filename suffix, but
    # every template here is named "*.xml.j2" (so editors still recognize
    # it as XML), which ends in ".j2" instead, so that selector never
    # actually matched and autoescaping was silently off: any field with
    # &, <, or > (a password, an OU path, ...) would corrupt the XML into
    # something Setup can't parse and silently falls back to interactive
    # install for, no visible error. Every template in this directory is
    # XML, so there's no need for a conditional selector at all.
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_autounattend(
    deployment: Deployment, template: DeploymentTemplate, disk_layout: DiskLayout
) -> str:
    """The single rendering entry point, both the wizard's preview step and
    the actual ISO build call this, so what an operator reviews is
    byte-identical to what ships."""
    tmpl = _ENV.get_template("autounattend_base.xml.j2")
    return tmpl.render(
        deployment=deployment,
        template=template,
        disk_layout=disk_layout,
        callback_base_url=get_settings().app_public_url,
    )
