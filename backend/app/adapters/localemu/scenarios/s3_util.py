"""S3 chores the scenarios share: empty a bucket, versions included, and clear a prefix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client
    from types_boto3_s3.type_defs import ObjectIdentifierTypeDef


def error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def empty_bucket(s3: S3Client, bucket: str) -> None:
    """Delete every object version and delete marker, so the bucket itself can go."""
    pages = s3.get_paginator("list_object_versions").paginate(Bucket=bucket)
    for page in pages:
        doomed: list[ObjectIdentifierTypeDef] = [
            {"Key": v["Key"], "VersionId": v["VersionId"]}
            for v in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]
            if "Key" in v and "VersionId" in v
        ]
        if doomed:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": doomed, "Quiet": True})


def delete_buckets(s3: S3Client, prefix: str) -> list[str]:
    """Every bucket whose name starts with `prefix`, emptied and deleted. Returns the names."""
    names = [
        b["Name"]
        for b in s3.list_buckets().get("Buckets", [])
        if b.get("Name", "").startswith(prefix)
    ]
    for name in names:
        try:
            empty_bucket(s3, name)
            s3.delete_bucket(Bucket=name)
        except ClientError as exc:
            if error_code(exc) != "NoSuchBucket":
                raise
    return names
