"""Figure `fig-cross-account-role`: cross-account access by assuming a role.

Drawn by `make figures` (docs/figures.md). Source: IAM tutorial, delegate access across
AWS accounts using IAM roles.
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.security import IAMAWSSts, IAMPermissions, IAMRole
from diagrams.aws.storage import S3

HERE = pathlib.Path(__file__).resolve().parent
NAME = "cross-account-role"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "Cross-account access: assume a role, receive temporary credentials",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    with Cluster("Account A: the caller"):
        app = EC2("Application on EC2")
        caller = IAMRole("Instance role\nmay call sts:AssumeRole")
    sts = IAMAWSSts("AWS STS")
    with Cluster("Account B: the resource owner"):
        role = IAMRole("Role for Account A\ntrust policy names Account A")
        perms = IAMPermissions("Permissions policy\nread one bucket")
        bucket = S3("Bucket")
    app - Edge(style="dashed") - caller
    caller >> Edge(label="AssumeRole") >> sts
    sts >> Edge(label="temporary credentials", style="dashed") >> role
    role - Edge(style="dotted") - perms
    role >> Edge(label="s3:GetObject") >> bucket

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"')
svg.write_text(text, encoding="utf-8")
