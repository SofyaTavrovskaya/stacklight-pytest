#!/usr/bin/env bash

apt install -y build-essential libssl-dev libffi-dev python-dev libyaml-dev python-dev python-pip

export LC_ALL=C

pip install virtualenv
pip install --upgrade pip
virtualenv --system-site-packages ../venv-stacklight-test
source ../venv-stacklight-test/bin/activate

pip install -r requirements.txt

cp openrc.default openrc

. openrc
