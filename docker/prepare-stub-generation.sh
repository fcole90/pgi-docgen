#!/usr/bin/env bash

echo "deb http://debug.mirrors.debian.org/debian-debug/ testing-debug main" >> /etc/apt/sources.list
rm /etc/apt/apt.conf.d/docker-no-languages

sudo apt update -y

sudo apt install -y \
    python3 \
    python3-pip \
    git \
    sudo \
    python3-lxml \
    graphviz \
    python3-apt \
    dctrl-tools \
    apt-file \
    xvfb \
    libgirepository-1.0 \
    gir1.2-glib-2.0
cd ~
mv install upstream_install
git clone https://github.com/fcole90/pgi-docgen.git install
cd install
export PYTHONPATH /home/user/install
export PYTHON=${PYTHON:-python3}
pip3 install --user --upgrade \
    "git+https://github.com/pygobject/pgi.git" \
    MarkupSafe==2.0.1 \
    requests==2.22.0 \
    jinja2==2.10.1 \
    sphinx==1.8.5 \
    cairocffi==1.0.2 \
    beautifulsoup4==4.7.1 \
    pytest \
    flake8 \
    coverage \
    pytest-cov
./pgi-docgen update-debian-info
./pgi-docgen create-debian _docs
./pgi-docgen build _docs _docs/_build
./pgi-docgen stubs _stubs Gtk-3.0
