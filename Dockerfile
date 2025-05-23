# ----------------------------------------
# Build python & hugo project
# ----------------------------------------
FROM python:3.10-alpine

ENV TRIVY_VERSION=v0.62.1
ENV CLAIRVOYANCE_VERSION=1.0.1

RUN apk add --no-cache curl build-base linux-headers \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin ${TRIVY_VERSION} \
    && pip install voyance==${CLAIRVOYANCE_VERSION}

ENTRYPOINT ["voyance"]
CMD ["--help"]
