import json

import pytest

from clairvoyance.notifiers.sqs import build_queue_url


class TestSqsNotifier:
    def test_build_queue_url(self):
        assert (
            build_queue_url("us-east-1", "123456789012", "backstage-trivy-reports")
            == "https://sqs.us-east-1.amazonaws.com/123456789012/backstage-trivy-reports"
        )

    def test_sqs(self, sqs_client, sqs_notifier, sqs_queue_url):
        message = {
            "ComponentName": "component",
            "RawReports": {"Image": {}, "Fs": {}},
            "Vulnerabilities": [
                {
                    "VulnerabilityCVEID": "CVE-2024-0001",
                    "PackageName": "openssl",
                    "PackageType": "os",
                }
            ],
            "Licenses": [
                {"Name": "MIT", "PackageName": "app", "PackageType": "library"}
            ],
        }

        sqs_notifier.send("Subject", message)

        messages = sqs_client.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=1,
        )["Messages"]
        body = json.loads(messages[0]["Body"])

        assert body == {
            "ComponentName": "component",
            "ProductSquad": "AdPlatform",
            "Vulnerabilities": message["Vulnerabilities"],
            "Licenses": message["Licenses"],
        }
        assert "RawReports" not in body

    def test_sqs_raises_without_message_id(self, sqs_notifier, mocker):
        sqs_notifier._sqs = mocker.Mock()
        sqs_notifier._sqs.send_message.return_value = {}

        with pytest.raises(RuntimeError, match="SQS did not return a message ID"):
            sqs_notifier.send("component", {})
