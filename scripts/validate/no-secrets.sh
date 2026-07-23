#!/usr/bin/env sh
set -eu

matches=$(git grep -nEI '(AKIA[0-9A-Z]{16}|BEGIN (RSA |EC )?PRIVATE KEY|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})' -- ':!*.lock' || true)
if [ -n "$matches" ]; then
  printf '%s\n' "$matches"
  exit 1
fi
