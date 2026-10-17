"""Figure `fig-vpc-two-tier`: a two-tier web app in a VPC, public and private subnets.

The source of `vpc-two-tier.svg`. Rendered with mingrammer/diagrams on Graphviz:

    uv run --no-project --with diagrams python -I vpc-two-tier.py

from this folder. The SVG is written beside the script with its icons inlined, so the
file is self-contained; `make figures` (rex/istari#80) will run every script here.
Drawn from the VPC User Guide's production example (two Availability Zones, a NAT
gateway in each): https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2, EC2AutoScaling
from diagrams.aws.database import RDS
from diagrams.aws.network import ALB, InternetGateway, NATGateway, Route53
from diagrams.onprem.client import Users

HERE = pathlib.Path(__file__).resolve().parent
NAME = "vpc-two-tier"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.6",
    "ranksep": "0.8",
}

with Diagram(
    "Two-tier web app in a VPC: public and private subnets",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    users = Users("Users")
    dns = Route53("Route 53")
    with Cluster("VPC 10.0.0.0/16"):
        igw = InternetGateway("Internet gateway")
        with Cluster("Public subnets (one per AZ)"):
            alb = ALB("Application Load Balancer")
            nat = NATGateway("NAT gateway")
        with Cluster("Private subnets: app tier"):
            asg = EC2AutoScaling("Auto Scaling group")
            web = [EC2("web a"), EC2("web b")]
        with Cluster("Private subnets: data tier"):
            db = RDS("RDS Multi-AZ")
    users >> dns >> igw >> alb >> web
    asg - Edge(style="dashed") - web
    web >> db
    web >> Edge(label="outbound only", style="dashed") >> nat >> igw

# Graphviz references the icon files by path; a figure must be self-contained.
svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(
        f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"'
    )
svg.write_text(text, encoding="utf-8")
