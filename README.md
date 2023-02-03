# :beginner: Clairvoyance - ECR Scan reports at your finger tips !

[![Build Status](https://cloud.drone.io/api/badges/Lowess/clairvoyance/status.svg)](https://cloud.drone.io/Lowess/clairvoyance)
[![Coverage Status](https://coveralls.io/repos/github/Lowess/clairvoyance/badge.svg?branch=master)](https://coveralls.io/github/Lowess/clairvoyance?branch=main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)
[![Linter: flake8](https://img.shields.io/badge/linter-flake8-blue.svg)](http://flake8.pycqa.org/en/latest/)
[![Linter: tests](https://img.shields.io/badge/tests-tox-yellow.svg)](hhttps://tox.readthedocs.io/en/latest)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)


> Clairvoyance is a simple [Hugo website](https://gohugo.io/) with capabilities to parse [ECR Security Scan reports](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)

Nothing is better than a live demo ! Here is an overview of [Clairvoyance](https://lowess.github.io/clairvoyance/) that ran against three vulnerable docker images hosted on ECR:

* [web-dvwa](https://hub.docker.com/r/vulnerables/web-dvwa)
* [eclipse-tumerin (old images)](https://hub.docker.com/_/eclipse-temurin/)
* [vulnerablewordpress](https://hub.docker.com/r/eystsen/vulnerablewordpress)

## :package: `Clairvoyance` - Architecture Diagram


![architecture-diagram-alt-text](docs/clairvoyance.excalidraw.png)

---
## `Clairvoyance` - Static Hugo Website

![reports-screenshot-alt-text](docs/screenshot-reports.png)

---

![repo-overview-screenshot-alt-text](docs/screenshot-repo-overview.png)

---

![repo-details-screenshot-alt-text](docs/screenshot-repo-details.png)

---

## Install `voyance` command line

```shell
pip install -e git+https://github.com/Lowess/clairvoyance@main#egg=clairvoyance
```

`voyance` is used to automatically generate Hugo content pages along with JSON data to easily visualize ECR scan reports. It scans the provided ECR registry as stated in the configuration file and look at a defined list of repositories and tagging patterns.

Here is a log sample you will get from `voyance` script execution:

| Env var                                  | Description                                                            | Example value                    |
| ---------------------------------------- | ---------------------------------------------------------------------- | -------------------------------- |
| `CLAIRVOYANCE_ECR__REGISTRY_ID`          | The ECR private registry id to scan (equals your AWS account id)       | `123456789012`                   |
| `CLAIRVOYANCE_ECR__REPOSITORIES`         | A list of ECR private repositories to get scans from                   | `'["repo1/app1", "repo2/app2"]'` |
| `CLAIRVOYANCE_ECR__ALLOWED_TAG_PATTERNS` | A list of tags or patterns to search for (can be a valid python regex) | `'["latest"]'`                   |

```shell
❯ voyance
2023-02-03 14:50:11,910,910      INFO credentials.py:1251 - Found credentials in shared credentials file: ~/.aws/credentials
2023-02-03 14:50:11,949,949      INFO voyance.py:84 - Clairvoyance initialized with EcrReporter configured to search in 3 repositories from registry 123456789012. Only images with ['.*'] tagging patterns will be scanned. [SnsNotifier configured to notify to SNS topic: arn:aws:sns:us-east-1:123456789012:topic-to-notify]
2023-02-03 14:50:15,539,539      INFO ecr.py:115 - Scan found for vulnerable/dvwa:latest
2023-02-03 14:50:16,015,015      INFO ecr.py:115 - Scan found for vulnerable/eclipse-temurin:11.0.13_8-jre-focal
2023-02-03 14:50:16,221,221      INFO ecr.py:115 - Scan found for vulnerable/eclipse-temurin:11.0.15_10-jre-focal
2023-02-03 14:50:16,526,526      INFO ecr.py:115 - Scan found for vulnerable/eclipse-temurin:11.0.14.1_1-jre-focal
2023-02-03 14:50:16,704,704      INFO ecr.py:115 - Scan found for vulnerable/eclipse-temurin:11.0.16.1_1-jre-focal
2023-02-03 14:50:17,772,772      INFO ecr.py:115 - Scan found for vulnerable/vulnerablewordpress:latest
2023-02-03 14:50:17,772,772      INFO voyance.py:46 - 6 scan reports found
2023-02-03 14:50:17,772,772      INFO voyance.py:27 - Function scan() took 5.82 seconds
2023-02-03 14:50:17,772,772      INFO ecr.py:152 - Generating report for dvwa/latest
2023-02-03 14:50:17,782,782      INFO ecr.py:152 - Generating report for eclipse-temurin/11.0.13_8-jre-focal
2023-02-03 14:50:17,783,783      INFO ecr.py:152 - Generating report for eclipse-temurin/11.0.15_10-jre-focal
2023-02-03 14:50:17,784,784      INFO ecr.py:152 - Generating report for eclipse-temurin/11.0.14.1_1-jre-focal
2023-02-03 14:50:17,785,785      INFO ecr.py:152 - Generating report for eclipse-temurin/11.0.16.1_1-jre-focal
2023-02-03 14:50:17,786,786      INFO ecr.py:152 - Generating report for vulnerablewordpress/latest
```
