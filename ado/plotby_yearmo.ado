*! version 0.2 02Jun2017 Mauricio Caceres, caceres@nber.org
*! Summarize variable by date

* WARNING: For `rolling' with `average' option, the function effectively
* assumes all missing values are 0, since it divides by the number of
* rows for a particular year-month. If missing should be missing then DO
* NOT use this option and use `stat' instead.

capture program drop plotby_yearmo
program plotby_yearmo
	syntax varlist [if] [in], ///
    [                         ///
        rolling(int 0)        /// Rolling stats by `rolling' months.
        stat(str)             /// [default = sum] Summary stat to use
        average               /// Take averages for the rolling stat
        autoadd               /// Add descriptions to titles
                              ///
        XADDvar(str)          /// [default = Total] Add in front of var labels
        TITLEFirst(str)       /// [default =`xaddvar'] Add before the title
        SUBTITLEFirst(str)    /// [default = ""] Subtitle (appears before auto sub)
        XFormat(str)          /// [default = ""] Display format of x-variable
        YFormat(str)          /// [default = ""] Display format of y-variable
        BYDays(real 20)       /// Display a month each 1 / `bydays' days
        BYMonths(real 3)      /// Display a level each `bymonths'th month
                              ///
                              ///
        fits(str)             /// [default = ""] Add line w/fit from `fits'
        bubble                /// Whether to overlay weighted scatter
        onlybubble            /// Whether to only plot weighted scatter
                              ///
        kwargs(str)           /// [default = ""] Arguments to pass to plot
    ]

    * Drop missing, subset
    * --------------------

    preserve
        marksample touse, novarlist
        keep if `touse'
        keep `varlist' `touse'
        tempvar ones counts yearmo datekeep

        * Get datevar, countvar, defaults
        * -------------------------------

        gettoken varlist whatcount: varlist
        if ("`whatcount'"  == "") local whatcount `touse'
        if ("`xaddvar'"    == "") local xaddvar Total
        if ("`stat'"       == "") local stat sum
        if ("`titlefirst'" == "") local titlefirst `xaddvar'

        * Summarize month-to-month
        * ------------------------

        sort `varlist'
        qui drop if mi(`varlist')
        qui gen `yearmo' = string(month(`varlist'))
        qui replace `yearmo' = "0" + `yearmo' if length(`yearmo') == 1
        qui replace `yearmo' = string(year(`varlist')) + `yearmo'

        local varlabel: variable label `varlist'
        if ( `:list sizeof stat' == 1 ) {
            foreach var in `whatcount' {
                local l`var': variable label `var'
            }
            local ccall (`stat') `whatcount'
        }
        else {
            local origcount `whatcount'
            local origxadd  `xaddvar'
            local tmpxadd   `origxadd'
            local whatcount ""
            local xaddvar   ""
            local ccall     ""
            foreach s in `stat' {
                gettoken xadd tmpxadd: tmpxadd
                local ccall   `ccall' (`s')
                foreach var in `origcount' {
                    local l`var'_`s': variable label `var'
                    local ccall `ccall' `var'_`s' = `var'
                    local whatcount `whatcount' `var'_`s'
                    local xaddvar   `xaddvar'   `xadd'
                }
            }
        }

        collapse (sum) `ones' = `touse' `ccall' ///
            (min) `datekeep' = `varlist', by(`yearmo')

        * If asked for rolling stats
        * --------------------------

        qui if (`rolling' > 0 & `rolling' < `:di _N') {
            if (`rolling' > 1 & "`autoadd'" != "") {
                local subtitles subtitle("`subtitlefirst', `rolling'-month rolling window")
            }
            else {
                local subtitles subtitle("`subtitlefirst'")
            }

            * Get potentially missing year-months
            * -----------------------------------

            merge 1:1 `yearmo' using $maindir/data/aux_yearmo, assert(2 3)
            sort `yearmo'
            replace `ones' = 0 if mi(`ones')

            * Compute rolling count
            * ---------------------

            foreach var in `whatcount' {
                replace `var'  = 0 if mi(`var')
                gen `var'o = `var'
            }
            tempvar ones2
            gen `ones2' = `ones'
            forvalues i = `rolling' / `:di _N' {
                local kstart = `i' - 1
                local kend   = `i' - `rolling' + 1
                di `kstart', `kend'
                forvalues k = `kstart'(-1)`kend' {
                    foreach var in `whatcount' {
                        replace `var'  = `var'[`i']  + `var'o[`k'] in `i'
                    }
                    replace `ones' = `ones'[`i'] + `ones2'[`k'] in `i'
                }
            }

            * If asked for mean
            * -----------------

            if "`average'" != "" {
                foreach var in `whatcount' {
                    list `var' in 1 / 2
                    replace `var'  = `var' / `ones'
                    list `var' in 1 / 2
                }
            }

            * First X values missing
            * ----------------------

            forvalues i = 1 / `:di `rolling' - 1' {
                foreach var in `whatcount' {
                    replace `var' = . in `i'
                }
                replace `datekeep' = . in `i'
            }
            drop if mi(`datekeep')
        }
        else {
            local subtitles subtitle("`subtitlefirst'")
        }

        * Display ticks by month
        * ----------------------

        tempvar nomiss
        gen byte `nomiss' = !mi(`datekeep')
        qui sum `datekeep' if `nomiss'
        local wmin = ceil(`r(min)')
        local wmax = floor(`r(max)')
        local wby  = floor((`wmax' - `wmin') / `bydays')
        di %td_NN/DD/CCYY `wmin', %td_NN/DD/CCYY `wmax'

        sort `datekeep'
        local wlabels ""
        forvalues i = 1 / `=_N' {
            if (mod(`i', `bymonths') == 0) local wlabels `wlabels' `:di `datekeep'[`i']'
        }

        * Format variables
        * ----------------

        if "`xformat'" != "" {
            format `datekeep' `xformat'
        }
        else {
            format `datekeep' %td_NN/CCYY
        }

        if "`yformat'" != "" {
            format `yformat' `whatcount'
        }

        * Labels and such
        * ---------------

        foreach var in `whatcount' {
            if ("`xaddvar'" == "") {
                label var `var' "Count `l`var''"
            }
            else {
                if ( `:list sizeof stat' == 1 ) {
                    label var `var' "`xaddvar' `l`var''"
                }
                else {
                    gettoken xadd xaddvar: xaddvar
                    label var `var' "`xadd' `l`var''"
                }
            }
        }

        label var `datekeep' "`varlabel'"
        if `rolling' > 1 {
            if "`autoadd'" != "" local tmpadd ", over `rolling' months"
            local title "`titlefirst'`tmpadd'"
        }
        else {
            if "`autoadd'" != "" local tmpadd ", by month"
            local title "`titlefirst'`tmpadd'"
        }

        * Plot the things!
        * ----------------

        if "`fits'" != "" & `:word count `whatcount'' < 2 {
            qui `fits' `whatcount' `datekeep'
            tempvar predict
            qui predict `predict'
            label var `predict' "Trend"
        }

        if ( "`bubble'" == "" ) {
            if ( "`fits'" == "" ) {
                * line `whatcount' `datekeep', xlabel(`wmin'(`wby')`wmax', angle(57))    ///
                *     title("`title'") `subtitles' `kwargs' legend(cols(1))
                line `whatcount' `datekeep', xlabel(`wlabels', angle(57)) ///
                    title("`title'") `subtitles' `kwargs' legend(cols(1))
            }
            else {
                * line `whatcount' `datekeep', xlabel(`wmin'(`wby')`wmax', angle(57))    ///
                line `whatcount' `datekeep', xlabel(`wlabels', angle(57)) ///
                ||  line `predict' `datekeep', mcolor(red)                ///
                    title("`title'") `subtitles' `kwargs'
            }
        }
        else if ( "`onlybubble'" == "" ) {
            if ( "`fits'" == "" ) {
                * scatter `whatcount' `datekeep' [aweight=`ones'],  mcolor(gs11)         ///
                * || line `whatcount' `datekeep', xlabel(`wmin'(`wby')`wmax', angle(57)) ///
                *     title("`title'") `subtitles' `kwargs' legend(cols(1))
                scatter `whatcount' `datekeep' [aweight=`ones'],  mcolor(gs11) ///
                || line `whatcount' `datekeep', xlabel(`wlabels', angle(57))   ///
                    title("`title'") `subtitles' `kwargs' legend(cols(1))
            }
            else {
                * scatter `whatcount' `datekeep' [aweight=`ones'],  mcolor(gs11)         ///
                * || line `whatcount' `datekeep', xlabel(`wmin'(`wby')`wmax', angle(57)) ///
                * || line `predict' `datekeep', mcolor(red)                              ///
                *     title("`title'") `subtitles' `kwargs'
                scatter `whatcount' `datekeep' [aweight=`ones'],  mcolor(gs11) ///
                || line `whatcount' `datekeep', xlabel(`wlabels', angle(57))   ///
                || line `predict' `datekeep', mcolor(red)                      ///
                    title("`title'") `subtitles' `kwargs'
            }
        }
        else {
            if ( "`fits'" == "" ) {
                * scatter `whatcount' `datekeep' [aweight=`ones'],          ///
                *     mcolor(gs11) xlabel(`wmin'(`wby')`wmax', angle(57))   ///
                *     title("`title'") `subtitles' `kwargs' legend(cols(1))
                scatter `whatcount' `datekeep' [aweight=`ones'], ///
                    mcolor(gs11) xlabel(`wlabels', angle(57))    ///
                    title("`title'") `subtitles' `kwargs' legend(cols(1))
            }
            else {
                * scatter `whatcount' `datekeep' [aweight=`ones'],          ///
                *     mcolor(gs11) xlabel(`wmin'(`wby')`wmax', angle(57))   ///
                * ||  line `predict' `datekeep', mcolor(red)                ///
                *     title("`title'") `subtitles' `kwargs'
                scatter `whatcount' `datekeep' [aweight=`ones'],          ///
                    mcolor(gs11) xlabel(`wlabels', angle(57))   ///
                ||  line `predict' `datekeep', mcolor(red)      ///
                    title("`title'") `subtitles' `kwargs'
            }
        }
    restore
end
