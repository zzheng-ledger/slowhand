#!/usr/bin/env bash

# `-e` exits on command failure.
# `-u` exits on unset variables.
# `-o` pipefail fails if any command in a pipeline fails.
set -euo pipefail

base_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pushd "$base_dir" || exit 1
trap 'popd' EXIT

echo "Cleaning ..."
rm -rf dist

echo "Syncing dependencies and building ..."
pdm sync
pdm build

shopt -s nullglob # if no file matches, let `whl_files` be empty
whl_files=(dist/slowhand-*-py3-none-any.whl)
if [ ${#whl_files[@]} -ne 1 ] || [ ! -f "${whl_files[0]}" ]; then
    echo "Error: Expected exactly one wheel file, found ${#whl_files[@]}"
    exit 1
fi
whl_file="${whl_files[0]}"
echo "Installing $whl_file ..."
pip install "$whl_file" --user --force-reinstall

echo "Checking ..."
slowhand version
