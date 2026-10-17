"""Figure `fig-nat-vs-endpoints`: a free gateway endpoint instead of the NAT gateway for S3
and DynamoDB traffic.

Drawn by `make figures` (docs/figures.md). Sources: VPC NAT gateways; AWS PrivateLink
gateway endpoints; Amazon VPC pricing.
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import Dynamodb
from diagrams.aws.general import InternetAlt1
from diagrams.aws.network import Endpoint, InternetGateway, NATGateway
from diagrams.aws.storage import S3

HERE = pathlib.Path(__file__).resolve().parent
NAME = "nat-vs-endpoints"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "S3 and DynamoDB from a private subnet: the gateway endpoint route costs nothing",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    with Cluster("VPC"):
        with Cluster("Private subnet"):
            instances = EC2("Instances")
        with Cluster("Public subnet"):
            nat = NATGateway("NAT gateway\nper hour and per gigabyte")
        igw = InternetGateway("Internet gateway")
        endpoint = Endpoint("Gateway endpoint\na route-table target, no charge")
    internet = InternetAlt1("Internet")
    s3 = S3("S3")
    dynamodb = Dynamodb("DynamoDB")
    instances >> Edge(label="0.0.0.0/0", color="firebrick") >> nat >> igw >> internet
    instances >> Edge(label="prefix-list route", color="darkgreen") >> endpoint >> [s3, dynamodb]

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"')
svg.write_text(text, encoding="utf-8")
