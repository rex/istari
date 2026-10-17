"""Figure `fig-sns-sqs-fan-out`: one event, several independent consumers.

Drawn by `make figures` (docs/figures.md). Sources: SNS common scenarios (fanout), SQS
dead-letter queues.
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2AutoScaling, Lambda
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.network import APIGateway

HERE = pathlib.Path(__file__).resolve().parent
NAME = "sns-sqs-fan-out"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "Fan-out: a topic in front of queues, each consumer scales and fails on its own",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    api = APIGateway("API Gateway")
    producer = Lambda("Order service")
    topic = SNS("Orders topic")
    with Cluster("One queue per consumer"):
        invoicing_q = SQS("Invoicing queue")
        shipping_q = SQS("Shipping queue")
        analytics_q = SQS("Analytics queue")
    invoicing = Lambda("Invoicing")
    shipping = EC2AutoScaling("Shipping workers")
    analytics = Lambda("Analytics")
    dlq = SQS("Dead-letter queue")
    api >> producer >> topic >> [invoicing_q, shipping_q, analytics_q]
    invoicing_q >> invoicing
    shipping_q >> shipping
    analytics_q >> analytics
    shipping_q >> Edge(label="after N failed receives", style="dashed") >> dlq

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"')
svg.write_text(text, encoding="utf-8")
