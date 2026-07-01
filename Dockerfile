# ----------------------------------------
# Build python & hugo project
# ----------------------------------------
FROM python:3.12-alpine

ENV TRIVY_VERSION=v0.71.0
ARG CLAIRVOYANCE_VERSION=1.1.2
ENV CLAIRVOYANCE_VERSION=${CLAIRVOYANCE_VERSION}

RUN apk add --no-cache curl build-base linux-headers \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin ${TRIVY_VERSION} \
    && pip install --no-cache-dir "setuptools>=68,<81" voyance==${CLAIRVOYANCE_VERSION}

ENTRYPOINT ["voyance"]
CMD ["--help"]
