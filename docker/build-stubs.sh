#!/bin/bash

set -e

TAG="lazka/pgi-docgen:v3"


sudo docker run --security-opt label=disable \
    --rm  --volume "$(pwd)/..:/home/user/app" \
    -t "${TAG}" ./pgi-docgen stubs _stubs
