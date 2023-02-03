#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
from datetime import datetime

import pytest

from clairvoyance.reporters import EcrReporter


class TestEcrReporter:
    @pytest.mark.parametrize(
        "reporter,given,expected",
        [
            (
                EcrReporter(
                    registry_id=None, repositories=[], allowed_tag_patterns=["latest"]
                ),
                "latest",
                True,
            ),
            (
                EcrReporter(
                    registry_id=None, repositories=[], allowed_tag_patterns=["latest"]
                ),
                "something",
                False,
            ),
            (
                EcrReporter(
                    registry_id=None, repositories=[], allowed_tag_patterns=["v.*"]
                ),
                "v1.0.1",
                True,
            ),
            (
                EcrReporter(
                    registry_id=None, repositories=[], allowed_tag_patterns=["v2.*"]
                ),
                "v1.0.2",
                False,
            ),
        ],
    )
    def test_is_allowed_pattern(self, reporter, given, expected):
        assert reporter._is_allowed_pattern(given) is expected

    def test_list_ecr_images(self, ecr_reporter, ecr_apps):
        total = 0
        for tags in ecr_apps.values():
            for tag in tags:
                total += 1 if ecr_reporter._is_allowed_pattern(tag) else 0

        found = ecr_reporter._list_ecr_images()

        assert len(found) == total

    def test_get_ecr_scan_findings(self, ecr_reporter, ecr_content):
        images = []
        for content in ecr_content:
            images.append(
                {
                    "repository": content["repositoryName"],
                    "tag": content["imageId"]["imageTag"],
                    "digest": content["imageId"]["imageDigest"],
                }
            )
        assert len(ecr_reporter._get_ecr_scan_findings(images)) == len(ecr_content)

    def test_report(self, tmp_path, ecr_reporter, ecr_content, ecr_apps):
        findings = []
        for content in ecr_content:
            content["imageScanFindings"] = {"imageScanCompletedAt": datetime.now()}
            findings.append(content)

        ecr_reporter.report(findings)

        # Similar to os.walk but with level addition
        # Taken from https://stackoverflow.com/a/234329
        def _walklevel(some_dir, level=1):
            some_dir = some_dir.rstrip(os.path.sep)
            assert os.path.isdir(some_dir)
            num_sep = some_dir.count(os.path.sep)
            for root, dirs, files in os.walk(some_dir):
                yield root, dirs, files
                num_sep_this = root.count(os.path.sep)
                if num_sep + level <= num_sep_this:
                    del dirs[:]

        # Ensure the appropriate directory layout is generated
        depth = 0
        expected_repositories = list(ecr_apps.keys())
        for _, dirs, files in _walklevel(str(tmp_path), level=3):
            # Under <toplevel> there should be two folders
            if depth == 0:
                assert dirs == ["content", "data"]
            # Inside <toplevel>/content there should a single folder
            if depth == 1:
                assert dirs == ["reports"]
            # Inside <toplevel>/content/reports there should be as many folders as image registry
            if depth == 2:
                assert dirs == expected_repositories
            # Inside <toplevel>/content/reports/<repo> there should be as many files as image tags + an index file
            if depth >= 3 and depth < (3 + len(expected_repositories)):
                assert dirs == []
                assert len(files) == len(ecr_apps[expected_repositories[depth - 3]]) + 1
                assert all(f.endswith(".md") for f in files)
                assert "_index.md" in files
            # Inside <toplevel>/data there should a single folder
            if depth == (3 + len(expected_repositories)):
                assert dirs == ["ecr"]
            # Inside <toplevel>/data/ecr there should as many json files as images
            if depth > (3 + len(expected_repositories)):
                assert dirs == []
                assert len(files) == sum(len(tags) for tags in ecr_apps.values())
                assert all(f.endswith(".json") for f in files)
            depth += 1
