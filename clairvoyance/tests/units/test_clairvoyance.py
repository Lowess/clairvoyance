#!/usr/bin/env python
# -*- coding: utf-8 -*-


class TestClairVoyance:
    def test_scan(self, clairvoyance_instance, ecr_content):
        clairvoyance_instance.scan()

    def test_report(self, clairvoyance_instance, ecr_content):
        clairvoyance_instance.report()

    def test_notify(self, clairvoyance_instance, ecr_content):
        clairvoyance_instance.notify()
