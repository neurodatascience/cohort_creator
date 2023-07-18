FROM python:3.10.9-bullseye

ARG DEBIAN_FRONTEND="noninteractive"

# install datalad
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        git git-annex && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir datalad && \
    git config --global --add user.name 'Ford Escort' && \
    git config --global --add user.email 42@H2G2.com && \
    datalad wtf

RUN mkdir -p /cohort_creator
WORKDIR /cohort_creator

COPY [".", "/cohort_creator"]
RUN pip install --no-cache-dir --upgrade pip==23.0.1 && \
    pip3 install --no-cache-dir -e .

ENTRYPOINT [ "/cohort_creator/entrypoint.sh" ]
COPY ["./docker/entrypoint.sh", \
    "/cohort_creator/entrypoint.sh"]
RUN chmod +x /cohort_creator/entrypoint.sh
