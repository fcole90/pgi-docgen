#!/bin/bash

# Example usage: "./build.sh Gtk-3.0"
# Result can be found in "_stubs/"

set -e

./pgi-docgen stubs _stubs "$@"
