"""Failing test for Smart-Doc training remote artifact uploader (TDD RED)."""

import sys
import types
from unittest.mock import MagicMock


def test_uploader_saves_to_s3():
    from src.smart_doc.training.artifacts import upload_artifact

    fake_s3 = MagicMock()
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(return_value=fake_s3)

    old_boto3 = sys.modules.get("boto3")
    sys.modules["boto3"] = fake_boto3
    try:
        import os

        os.environ["ARTIFACT_BUCKET"] = "test-bucket"
        result = upload_artifact(data=b"test", key="test.pt")
    finally:
        if old_boto3 is not None:
            sys.modules["boto3"] = old_boto3
        else:
            sys.modules.pop("boto3", None)

    assert "s3://" in result or result.startswith("http")
    assert result == "s3://test-bucket/test.pt"
    fake_s3.put_object.assert_called_once_with(
        Bucket="test-bucket", Key="test.pt", Body=b"test"
    )
