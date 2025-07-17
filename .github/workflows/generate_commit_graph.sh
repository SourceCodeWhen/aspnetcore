#!/bin/bash

set -e

# Parameters
REPO_PATH=${1:-.}
OUTPUT_SVG=${2:-commit-graph.svg}
SINCE_DATE=${3:-""}

# Install Rust if not present
if ! command -v cargo >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install git-graph
if ! command -v git-graph >/dev/null; then
  cargo install git-graph
fi

cd "$REPO_PATH"

# Build git-graph arguments
args=("--svg" "-o" "$OUTPUT_SVG" "--show-authors" "--show-branches" "--show-merges" "--show-dates" "--width" "2048")
if [[ -n "$SINCE_DATE" ]]; then
  args+=("--since" "$SINCE_DATE")
fi

# Generate SVG graph
git-graph "${args[@]}"
echo "Generated $OUTPUT_SVG"
