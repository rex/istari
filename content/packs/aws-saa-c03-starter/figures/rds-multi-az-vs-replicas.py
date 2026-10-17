"""Figure `fig-rds-multi-az-vs-replicas`: Multi-AZ is for failover, replicas are for reads.

Drawn by `make figures` (docs/figures.md). Sources: Amazon RDS Multi-AZ DB instance
deployments; Amazon RDS read replicas.
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS, RDSInstance

HERE = pathlib.Path(__file__).resolve().parent
NAME = "rds-multi-az-vs-replicas"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "Multi-AZ keeps one endpoint alive; read replicas add readers",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    app = EC2("Application")
    with Cluster("Multi-AZ DB instance: one endpoint, failover in minutes"):
        with Cluster("AZ a"):
            primary = RDS("Primary")
        with Cluster("AZ b"):
            standby = RDS("Standby\nsynchronous, not readable")
    with Cluster("Read replicas: a reader endpoint, promotable"):
        local = RDSInstance("Replica in the Region\nasynchronous, readable")
        remote = RDSInstance("Replica in another Region\nalso a DR seed")
    app >> Edge(label="writes and reads") >> primary
    primary >> Edge(label="synchronous replication", style="dashed") >> standby
    primary >> Edge(label="asynchronous") >> [local, remote]
    app >> Edge(label="reads", style="dashed") >> local

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"')
svg.write_text(text, encoding="utf-8")
