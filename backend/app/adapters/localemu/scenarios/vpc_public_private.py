"""A VPC with a public and a private subnet: an internet gateway, a NAT gateway, two routes.

Setup makes an empty VPC (10.0.0.0/16) tagged `Name=<prefix>`. The learner adds a public
subnet whose route table sends 0.0.0.0/0 to an internet gateway, a NAT gateway in that public
subnet, and a private subnet whose route table sends 0.0.0.0/0 to the NAT gateway. The check
reads the subnets, their route tables (explicit associations, else the VPC's main table), the
attached internet gateways and the NAT gateways, so any CIDRs and names will do.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.localemu.aws import Aws
from app.adapters.localemu.scenario import Scenario, ScenarioContext
from app.adapters.localemu.scenarios.grading import Clause, gone, verdict
from app.domain.verifier import CheckResult

if TYPE_CHECKING:
    from types_boto3_ec2.client import EC2Client
    from types_boto3_ec2.type_defs import FilterTypeDef, NatGatewayTypeDef, RouteTableTypeDef

ANYWHERE = "0.0.0.0/0"
VPC_CIDR = "10.0.0.0/16"
LIVE_NAT = ("pending", "available")


def _in_vpc(vpc: str) -> list[FilterTypeDef]:
    return [{"Name": "vpc-id", "Values": [vpc]}]


def _nat_gateways(ec2: EC2Client, vpc: str) -> list[NatGatewayTypeDef]:
    """The VPC's NAT gateways, filtered here: the API's parameter is `Filter`, which the type
    stubs spell `Filters`, so an unfiltered call keeps both honest."""
    return [n for n in ec2.describe_nat_gateways()["NatGateways"] if n.get("VpcId") == vpc]


def _vpc_ids(ec2: EC2Client, name_prefix: str) -> list[str]:
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag-key", "Values": ["Name"]}])["Vpcs"]
    return [
        v["VpcId"]
        for v in vpcs
        if any(
            t.get("Key") == "Name" and t.get("Value", "").startswith(name_prefix)
            for t in v.get("Tags", [])
        )
    ]


def setup(aws: Aws, ctx: ScenarioContext) -> str:
    vpc = aws.ec2().create_vpc(
        CidrBlock=VPC_CIDR,
        TagSpecifications=[{"ResourceType": "vpc", "Tags": [{"Key": "Name", "Value": ctx.prefix}]}],
    )["Vpc"]["VpcId"]
    return f"VPC {vpc} ({VPC_CIDR}, Name tag {ctx.prefix}) is ready: no subnets, no gateways."


def _default_target(table: RouteTableTypeDef) -> str:
    """Where the table sends 0.0.0.0/0: an igw- or nat- id, or '' when it has no such route."""
    for route in table.get("Routes", []):
        if route.get("DestinationCidrBlock") == ANYWHERE:
            return route.get("NatGatewayId") or route.get("GatewayId") or ""
    return ""


def _targets_by_subnet(ec2: EC2Client, vpc: str, subnets: list[str]) -> dict[str, str]:
    """Each subnet's default-route target, through its own route table or the main one."""
    tables = ec2.describe_route_tables(Filters=_in_vpc(vpc))["RouteTables"]
    main = next((t for t in tables if any(a.get("Main") for a in t.get("Associations", []))), None)
    explicit = {
        a["SubnetId"]: t for t in tables for a in t.get("Associations", []) if a.get("SubnetId")
    }
    return {
        subnet: _default_target(explicit[subnet])
        if subnet in explicit
        else (_default_target(main) if main is not None else "")
        for subnet in subnets
    }


def check(aws: Aws, ctx: ScenarioContext) -> CheckResult:
    ec2 = aws.ec2()
    vpcs = _vpc_ids(ec2, ctx.prefix)
    if not vpcs:
        return gone(f"The VPC tagged {ctx.prefix}")
    vpc = vpcs[0]
    subnets = [s["SubnetId"] for s in ec2.describe_subnets(Filters=_in_vpc(vpc))["Subnets"]]
    igws = {
        g["InternetGatewayId"]
        for g in ec2.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc]}]
        )["InternetGateways"]
    }
    nats = [n for n in _nat_gateways(ec2, vpc) if n.get("State") in LIVE_NAT]
    targets = _targets_by_subnet(ec2, vpc, subnets)
    public = {s for s, target in targets.items() if target in igws}
    nat_ids = {n.get("NatGatewayId", "") for n in nats}
    private = {s for s, target in targets.items() if target in nat_ids}
    clauses = [
        Clause(
            bool(igws),
            "an internet gateway is attached to the VPC",
            "attach an internet gateway to the VPC",
        ),
        Clause(
            bool(public),
            f"public subnet {', '.join(sorted(public))}: {ANYWHERE} goes to the internet gateway",
            f"no subnet's route table sends {ANYWHERE} to an attached internet gateway",
        ),
        Clause(
            any(n.get("SubnetId") in public for n in nats),
            "a NAT gateway sits in a public subnet",
            "put a NAT gateway in the public subnet (it reaches the internet through it)",
        ),
        Clause(
            bool(private),
            f"private subnet {', '.join(sorted(private))}: {ANYWHERE} goes to the NAT gateway",
            f"no subnet's route table sends {ANYWHERE} to the NAT gateway",
        ),
    ]
    header = (
        f"VPC {vpc}: {len(subnets)} subnet(s), {len(igws)} internet gateway(s), "
        f"{len(nats)} NAT gateway(s)"
    )
    return verdict(header, clauses, "public subnet out through the IGW, private through the NAT")


def solve(aws: Aws, ctx: ScenarioContext) -> None:
    ec2 = aws.ec2()
    vpc = _vpc_ids(ec2, ctx.prefix)[0]
    public = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"]
    private = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.2.0/24")["Subnet"]["SubnetId"]
    igw = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw, VpcId=vpc)
    eip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    nat = ec2.create_nat_gateway(SubnetId=public, AllocationId=eip)["NatGateway"]["NatGatewayId"]
    public_table = ec2.create_route_table(VpcId=vpc)["RouteTable"]["RouteTableId"]
    ec2.create_route(RouteTableId=public_table, DestinationCidrBlock=ANYWHERE, GatewayId=igw)
    ec2.associate_route_table(RouteTableId=public_table, SubnetId=public)
    private_table = ec2.create_route_table(VpcId=vpc)["RouteTable"]["RouteTableId"]
    ec2.create_route(RouteTableId=private_table, DestinationCidrBlock=ANYWHERE, NatGatewayId=nat)
    ec2.associate_route_table(RouteTableId=private_table, SubnetId=private)


def _clear_vpc(ec2: EC2Client, vpc: str) -> None:
    in_vpc = _in_vpc(vpc)
    for nat in _nat_gateways(ec2, vpc):
        if nat.get("State") in LIVE_NAT:
            ec2.delete_nat_gateway(NatGatewayId=nat["NatGatewayId"])
        for address in nat.get("NatGatewayAddresses", []):
            if address.get("AllocationId"):
                ec2.release_address(AllocationId=address["AllocationId"])
    attached: list[FilterTypeDef] = [{"Name": "attachment.vpc-id", "Values": [vpc]}]
    for igw in ec2.describe_internet_gateways(Filters=attached)["InternetGateways"]:
        ec2.detach_internet_gateway(InternetGatewayId=igw["InternetGatewayId"], VpcId=vpc)
        ec2.delete_internet_gateway(InternetGatewayId=igw["InternetGatewayId"])
    for table in ec2.describe_route_tables(Filters=in_vpc)["RouteTables"]:
        associations = table.get("Associations", [])
        if any(a.get("Main") for a in associations):
            continue
        for association in associations:
            ec2.disassociate_route_table(AssociationId=association["RouteTableAssociationId"])
        ec2.delete_route_table(RouteTableId=table["RouteTableId"])
    for subnet in ec2.describe_subnets(Filters=in_vpc)["Subnets"]:
        ec2.delete_subnet(SubnetId=subnet["SubnetId"])
    ec2.delete_vpc(VpcId=vpc)


def teardown(aws: Aws, ctx: ScenarioContext) -> None:
    ec2 = aws.ec2()
    for vpc in _vpc_ids(ec2, ctx.scenario_prefix):
        _clear_vpc(ec2, vpc)


SCENARIO = Scenario(
    id="vpc-public-private",
    profile="saa",
    title="A public and a private subnet: internet gateway out, NAT gateway out",
    context=(
        f"Setup creates an empty VPC in the emulator ({VPC_CIDR}) whose Name tag starts with "
        "istari-vpc-public-private-; the setup output gives its id. It has no subnets and no "
        "gateways."
    ),
    task=(
        "Build the classic two-tier layout. Add a public subnet whose route table sends "
        f"{ANYWHERE} to an internet gateway attached to the VPC, a NAT gateway in that public "
        "subnet (it needs an Elastic IP), and a private subnet whose route table sends "
        f"{ANYWHERE} to the NAT gateway, so instances there reach out without being reachable. "
        "Use the AWS CLI pointed at the emulator, then run the check."
    ),
    hint=(
        "create-subnet twice; create-internet-gateway and attach-internet-gateway; "
        "allocate-address --domain vpc and create-nat-gateway in the public subnet; then for "
        "each subnet create-route-table, create-route --destination-cidr-block 0.0.0.0/0 "
        "(--gateway-id igw-... or --nat-gateway-id nat-...) and associate-route-table."
    ),
    setup=setup,
    check=check,
    teardown=teardown,
    solve=solve,
)
