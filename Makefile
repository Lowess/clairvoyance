.PHONY: dev tests nginx

dev:
	pip install --editable .
	pip install --editable .[tests]

tests:
	tox run

nginx:
	hugo --baseUrl localhost:8081
	docker run -it --rm \
		-v ${PWD}/public:/usr/share/nginx/html:ro \
		-p 8081:80 \
		nginx:stable-alpine
