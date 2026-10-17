"""Figure `fig-three-storage-kinds`: block, file and object storage, and who can reach each.

Drawn by `make figures` (docs/figures.md). Sources: Amazon EBS volume types; What is
Amazon Elastic File System; Amazon S3 best practices (performance).
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.storage import EBS, EFS, S3
from diagrams.onprem.client import Users

HERE = pathlib.Path(__file__).resolve().parent
NAME = "three-storage-kinds"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.8",
}

with Diagram(
    "Block, file, object: how many readers, from where",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="TB",
    graph_attr=GRAPH_ATTR,
):
    with Cluster("Block: one instance, one Availability Zone"):
        one = EC2("Instance")
        ebs = EBS("EBS volume\nboot disks, databases")
        one - Edge(label="attached") - ebs
    with Cluster("File: many instances, several Availability Zones"):
        many_a = EC2("Instance")
        many_b = EC2("Instance")
        efs = EFS("EFS file system\nNFS, grows on its own")
        [many_a, many_b] - Edge(label="mounted") - efs
    with Cluster("Object: anything that speaks HTTP"):
        users = Users("Users")
        functions = Lambda("Functions")
        s3 = S3("S3 bucket\nwhole objects, eleven nines")
        [users, functions] >> s3

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(
        f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"'
    )
svg.write_text(text, encoding="utf-8")
