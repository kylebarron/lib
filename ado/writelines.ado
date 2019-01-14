*! version 1.0.0 02jan2019
// Write list of lines of text to file

cap program drop writelines
program writelines
    syntax, file(str) text(str) [noaddeol replace append]

    if ("`replace'`append'" == "replaceappend") {
        di as err "replace and append are mutually exclusive"
        exit 1
    }

    if ("`addeol'" == "noaddeol") {
        local eol ""
    }
    else if ("`c(os)'" == "Unix" | "`c(os)'" == "MacOSX") {
        local eol "`=char(10)'"
    }
    else {
        local eol "`=char(13)'`=char(10)'"
    }

    // Open file
    tempname f
    file open `f' using `"`file'"', write text `replace' `append'

    qui cap {
        foreach word of local text {
            file write f `"`word'`eol'"'
        }
    }
    local rc = _rc

    // Close file
    file close `f'

    if (`rc' != 0) {
        exit `rc'
    }
end
