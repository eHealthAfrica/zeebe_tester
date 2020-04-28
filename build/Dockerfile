FROM python:3.7-slim-stretch

################################################################################
## setup container
################################################################################

################################################################################
## install app
## copy files one by one and split commands to use docker cache
################################################################################

RUN apt-get update -qq && \
    apt-get -qq \
        --yes \
        --allow-downgrades \
        --allow-remove-essential \
        --allow-change-held-packages \
        install gcc && \
    pip install -q --upgrade pip

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip3 install -r /code/requirements.txt

COPY ./ /code

################################################################################
## last setup steps
################################################################################

# create user to run container (avoid root user)
RUN useradd -ms /bin/false aether
RUN chown -R aether: /code

ENTRYPOINT ["/code/entrypoint.sh"]
