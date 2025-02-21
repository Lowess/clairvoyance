#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging

import boto3
import helpers
import pytest
from moto import mock_ecr, mock_sns

from clairvoyance.notifiers import SnsNotifier, StdoutNotifier
from clairvoyance.reporters.ecr_native import EcrNativeReporter
from clairvoyance.voyance import Clairvoyance

logger = logging.getLogger()


@pytest.fixture
def ecr_client():
    """Mock ECR client"""
    with mock_ecr():
        yield boto3.client("ecr")


@pytest.fixture
def sns_client():
    """Mock SNS client"""
    with mock_sns():
        yield boto3.client("sns")


@pytest.fixture
def registry_id():
    """Mock registry id"""
    return "123456789012"


@pytest.fixture
def ecr_apps():
    """Mock content to populate ECR registry"""
    return {
        "test-app1": ["latest", "v1.0.0", "v1.0.1"],
        "test-app2": ["latest", "v2.0.0", "v2.0.2"],
        "db-test": ["latest", "v3.0.0"],
    }


@pytest.fixture
def ecr_content(ecr_client, ecr_apps):
    """Mock ECR registry with fake container repos and versions"""
    images = []
    for repo, tags in ecr_apps.items():
        # Create an ECR repo
        ecr_client.create_repository(
            repositoryName=repo,
            imageScanningConfiguration={"scanOnPush": True},
        )

        for tag in tags:
            # Put the docker image
            image = ecr_client.put_image(
                repositoryName=repo,
                imageManifest=json.dumps(helpers._create_image_manifest()),
                imageTag=tag,
            )["image"]

            images.append(image)

            # Starting the scan of the image.
            ecr_client.start_image_scan(
                repositoryName=repo,
                imageId={"imageTag": tag},
            )
    return images


@pytest.fixture
def sns_topic(sns_client):
    """Mock SNS topic and return the topic ARN"""
    return sns_client.create_topic(Name="mock")["TopicArn"]


@pytest.fixture
def allowed_patterns():
    return ["v.*", "latest"]


@pytest.fixture()
def ecr_reporter(
    tmp_path, allowed_patterns, registry_id, ecr_client, ecr_apps, ecr_content
):
    """Create an EcrReporter object with a mocked ECR client"""
    reporter = EcrNativeReporter(
        registry_id=registry_id,
        repositories=ecr_apps.keys(),
        allowed_tag_patterns=[allowed_patterns],
        report_folder=tmp_path,
    )
    # Subsititue with mocked boto client
    reporter._ecr = ecr_client
    yield reporter


@pytest.fixture
def sns_notifier(sns_client, sns_topic):
    """Create an SnsNotifier object with a mocked SNS client"""
    notifier = SnsNotifier(topic_arn=sns_topic)
    # Subsititue with mocked boto client
    notifier._sns = sns_client
    yield notifier


@pytest.fixture
def clairvoyance_instance(ecr_reporter, sns_notifier):
    """Main Clairvoyance object with mocked objects"""
    yield Clairvoyance(
        reporter=ecr_reporter,
        notifiers=[sns_notifier, StdoutNotifier()],
    )
