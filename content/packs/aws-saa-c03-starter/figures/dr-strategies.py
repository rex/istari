"""Figure `fig-dr-strategies`: the four disaster recovery strategies on one line.

Drawn by `make figures` (docs/figures.md). Source: Disaster recovery options in the cloud
(the AWS whitepaper).
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2AutoScaling
from diagrams.aws.database import RDS
from diagrams.aws.network import Route53
from diagrams.aws.storage import Backup

HERE = pathlib.Path(__file__).resolve().parent
NAME = "dr-strategies"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "1.0",
}

with Diagram(
    "Four DR strategies: cheaper to the left, faster to recover to the right",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    with Cluster("Backup and restore\nRPO and RTO: hours"):
        restore = Backup("Backups in the other Region\nrebuild on demand")
    with Cluster("Pilot light\nRPO and RTO: tens of minutes"):
        pilot = RDS("Data replicated live\ncompute switched off")
    with Cluster("Warm standby\nRPO and RTO: minutes"):
        warm = EC2AutoScaling("A scaled-down copy runs\nscale up on failover")
    with Cluster("Multi-site active/active\nRPO and RTO: near zero"):
        active = Route53("Both Regions serve traffic\nDNS shifts the share")
    restore >> Edge(label="more cost") >> pilot >> Edge(label="less downtime") >> warm >> active

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"')
svg.write_text(text, encoding="utf-8")
