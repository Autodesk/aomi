FROM python:2.7

MAINTAINER 'Jonathan Freedman <jonathan.freedman@autodesk.com>'
ARG VERSION=0.0.0

LABEL license="MIT"
LABEL version="${VERSION}"

ADD . /tmp/aomi
ADD scripts/docker-entrypoint /usr/local/bin/docker-entrypoint

RUN cd /tmp/aomi && python setup.py install && cd /tmp && rm -rf /tmp/aomi

ENTRYPOINT ["docker-entrypoint"]
