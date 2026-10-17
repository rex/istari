"""Figure `fig-envelope-encryption`: a KMS key wraps the data key that encrypts the object.

Drawn by `make figures` (docs/figures.md). Source: AWS KMS concepts (envelope encryption).
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.security import KMS
from diagrams.aws.security import (
    IdentityAndAccessManagementIamDataEncryptionKey as DataKey,
)
from diagrams.aws.security import (
    IdentityAndAccessManagementIamEncryptedData as EncryptedData,
)
from diagrams.aws.storage import S3

HERE = pathlib.Path(__file__).resolve().parent
NAME = "envelope-encryption"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "Envelope encryption: the KMS key never leaves KMS; a data key does the work",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    kms = KMS("KMS key\nnever leaves KMS")
    plain = DataKey("Plaintext data key\nused once, discarded")
    with Cluster("Stored together in S3"):
        obj = S3("Encrypted object")
        wrapped = EncryptedData("Encrypted data key\nsent back to KMS to decrypt")
    kms >> Edge(label="GenerateDataKey") >> plain
    plain >> Edge(label="encrypts") >> obj
    kms >> Edge(label="encrypted copy", style="dashed") >> wrapped

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(
        f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"'
    )
svg.write_text(text, encoding="utf-8")
