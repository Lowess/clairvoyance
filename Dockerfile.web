# ----------------------------------------
# Build python & hugo project
# ----------------------------------------
FROM peaceiris/hugo:v0.104.3-full as builder

ARG HUGO_BASE_URL="/"
ENV HUGO_BASE_URL=${HUGO_BASE_URL}

WORKDIR /src

COPY . /src

RUN cd /src \
    && ls -al \
    && hugo -b ${HUGO_BASE_URL}

# ----------------------------------------
# Run from nginx
# ----------------------------------------
FROM nginx:alpine

COPY --from=builder /src/public /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
