#!/usr/bin/env bash
docker create -i --name upstream-pgi-docgen lazka/pgi-docgen:v3
docker start upstream-pgi-docgen
docker exec -it upstream-pgi-docgen bash
