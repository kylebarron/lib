#! /usr/bin/env bash
# Check Stata log for errors and issue a non-zero return code if an error
# occurred.
#
# The idea for this came from
# https://gist.github.com/pschumm/b967dfc7f723507ac4be

# Accepts either:
#   a single argument, the log file
#   the log file piped to stdin

if egrep --before-context=1 --max-count=1 "^r\([0-9]+\);$" "${1:-/dev/stdin}"
then
    exit 1
else
    exit 0
fi
