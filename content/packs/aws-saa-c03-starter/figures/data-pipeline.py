"""Figure `fig-data-pipeline`: from streams and on-premises files to SQL on a data lake.

Drawn by `make figures` (docs/figures.md). Sources: What is Amazon Kinesis Data Streams;
What is Amazon Data Firehose; What is AWS Glue; What is Amazon Athena; What is AWS DataSync.
"""

import base64
import pathlib
import re

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import (
    Athena,
    GlueCrawlers,
    GlueDataCatalog,
    KinesisDataFirehose,
    KinesisDataStreams,
    Quicksight,
)
from diagrams.aws.migration import Datasync
from diagrams.aws.storage import S3
from diagrams.onprem.compute import Server

HERE = pathlib.Path(__file__).resolve().parent
NAME = "data-pipeline"
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "pad": "0.4",
    "nodesep": "0.5",
    "ranksep": "0.9",
}

with Diagram(
    "A data lake on S3: ingest, catalog, query, visualize",
    filename=str(HERE / NAME),
    outformat="svg",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
):
    with Cluster("Ingest"):
        streams = KinesisDataStreams("Kinesis Data Streams\nreal time, shards")
        firehose = KinesisDataFirehose("Data Firehose\nbuffer, convert, deliver")
        onprem = Server("On-premises file share")
        datasync = Datasync("DataSync\nscheduled transfers")
    lake = S3("Data lake\nraw and curated prefixes")
    with Cluster("Catalog and query"):
        crawler = GlueCrawlers("Glue crawler")
        catalog = GlueDataCatalog("Data Catalog\ntables over S3")
        athena = Athena("Athena\nSQL, pay per scan")
        quicksight = Quicksight("QuickSight")
    streams >> firehose >> lake
    onprem >> datasync >> lake
    lake >> crawler >> catalog >> athena >> quicksight
    lake >> Edge(style="dashed") >> athena

svg = HERE / f"{NAME}.svg"
text = svg.read_text(encoding="utf-8")
for ref in set(re.findall(r'xlink:href="([^"]+\.png)"', text)):
    data = base64.b64encode(pathlib.Path(ref).read_bytes()).decode()
    text = text.replace(
        f'xlink:href="{ref}"', f'xlink:href="data:image/png;base64,{data}"'
    )
svg.write_text(text, encoding="utf-8")
