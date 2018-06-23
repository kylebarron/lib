#! /usr/bin/env bash
# Wrapper for "stata -b" which issues an informative error msg and appropriate
# (i.e., non-zero) return code

# The basic idea for this script (including grepping the log file to determine
# whether there was an error) was taken from a similar script posted by Brendan
# Halpin on his blog at http://teaching.sociology.ul.ie/bhalpin/wordpress/?p=122

# This script was forked from https://gist.github.com/pschumm/b967dfc7f723507ac4be

# Add support for old, __really old__ versions of GNU coreutils
# The -s switch to basename was added in 2012
# https://github.com/adtools/coreutils/blob/f94b6dd850452b3260397caee6f983ef59f25df1/ChangeLog#L15748

args=$#  # number of args
basename_year="$(basename --version | grep opyright | grep -oP '\d{4}')"


if [[ -x "$(command -v stata-mp)" ]]; then
    STATA_FLAVOR="stata-mp"
elif [[ -x "$(command -v stata-se)" ]]; then
    STATA_FLAVOR="stata-se"
elif [[ -x "$(command -v stata-ic)" ]]; then
    STATA_FLAVOR="stata-ic"
elif [[ -x "$(command -v stata)" ]]; then
    STATA_FLAVOR="stata"
fi


cmd=""
if [ "$1" = "do" ] && [ "$args" -gt 1 ]
then
    if [[ "$basename_year" -lt 2013 ]]; then
        # This just takes the last three characters off
        log="$(echo ${2%???}).log"
    else
        log="$(basename -s .do "$2").log"
    fi
    # mimic Stata's behavior (stata-mp -b do "foo bar.do" -> foo.log)
    log=${log/% */.log}
# Stata requires explicit -do- command, but we relax this to permit just the
# name of a single do-file
elif [ "$args" -eq 1 ] && [ "${1##*.}" = "do" ] && [ "$1" != "do" ]
then
    cmd="do"
    if [[ "$basename_year" -lt 2013 ]]; then
        # This just takes the last three characters off
        log="$(echo ${1%???}).log"
    else
        log="$(basename -s .do "$1").log"
    fi
    log=${log/% */.log}
else
    # else Stata interprets it as a command and logs to stata.log
    log="stata.log"
fi

# in batch mode, nothing sent to stdout (is this guaranteed?)
stderr=$($STATA_FLAVOR -b $cmd "$@" 2>&1)
rc=$?
if [ -n "$stderr" ]  # typically usage info
then
    echo "$stderr"
    exit $rc
elif [ $rc != "0" ]
then
    exit $rc
else
    # use --max-count to avoid matching final line ("end of do-file") when
    # do-file terminates with error
    if egrep --before-context=1 --max-count=1 "^r\([0-9]+\);$" "$log"
    then
        exit 1
    fi
fi
