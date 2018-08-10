*! version 0.2 30May2017 Mauricio Caceres, caceres@nber.org
*! Graph export to pdf (Unix)

capture program drop gexport_unix
program gexport_unix
    syntax anything, [convert replace dpi(int 150)]
    gettoken 0 1: anything, p(,)
    qui graph export   "`0'.eps" `1', `replace'
    if ( "`convert'" == "convert" ) {
        qui shell convert -density `dpi' "`0'.eps" "`0'.pdf"
        qui shell rm -f   "`0'.eps"
    }
    else {
        qui shell epstopdf "`0'.eps"
        qui shell rm -f    "`0'.eps"
    }
end
