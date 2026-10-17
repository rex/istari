"""Figure `fig-s3-storage-classes`: a lifecycle moves objects down the classes as access fades.

Drawn by `make figures` (docs/figures.md). Sources: Amazon S3 storage classes; Managing the
lifecycle of objects; Amazon S3 Intelligent-Tiering.
"""

import base64
import pathlib
import re

from diagrams import Diagram, Edge
from diagrams.aws.storage import S3, S3Glacier, S3GlacierArchive
from diagrams.generic.blank import Blank

HERE = pathlib.Path(__file__).resolve().parent
NAME = "s3-storage-classes"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.8",
    "nodesep": "0.6",
    "ranksep": "1.0",
}

with Diagram(
    "Each step down costs less to keep and more to get back",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    standard = S3("S3 Standard\nfrequent access")
    tiering = S3("Intelligent-Tiering\nmoves objects itself")
    infrequent = S3("Standard-IA\nretrieval fee\nat least 30 days")
    flexible = S3Glacier("Glacier Flexible\nminutes to hours\nat least 90 days")
    deep = S3GlacierArchive("Deep Archive\nabout 12 hours\nat least 180 days")
    expired = Blank("Expired")
    (
        standard
        >> Edge(label="transition")
        >> infrequent
        >> Edge(label="transition")
        >> flexible
    )
    (
        flexible
        >> Edge(label="transition")
        >> deep
        >> Edge(label="expire", style="dotted")
        >> expired
    )
    standard >> Edge(label="unknown access pattern", style="dashed") >> tiering

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(
        f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"'
    )
svg.write_text(text, encoding="utf-8")
