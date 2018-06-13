#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from os import path, linesep, getcwd, chdir, system
from os import symlink, unlink, makedirs, listdir
from collections import Iterable as Iter, OrderedDict
from datetime import datetime
from sys import version_info
from shutil import rmtree, copy2
from time import sleep
import argparse
import sys
import re

def main():
    # I think this can also be run from Makefile.py directly (NOT TESTED!)
    # from make import MakeInternals  # noqa
    # make = MakeInternals()
    # make.set_options()
    # make.start_logging()
    # make.run_directly(todo)

    make = MakeInternals()
    make.parse_cli()
    make.start_logging()
    make.check_targets()
    make.run_targets()


class MakeInternals():

    """Main object for make module"""

    def __init__(self):
        self.timestampts = OrderedDict()

    def timer(self, target, name):
        nowdt  = datetime.now()
        nowstr = nowdt.strftime("%H:%M %a %b %d, %Y")
        if target not in self.timestampts.keys():
            self.timestampts[target] = OrderedDict()

        i = 1
        names  = self.timestampts[target].keys()
        nameok = name
        while nameok in names:
            nameok = name + " ({0})".format(i)
            i += 1

        self.timestampts[target][nameok] = nowstr, nowdt

    def set_options(self,
                    tags         = [],
                    run_all      = False,
                    dryrun       = False,
                    gen_bash     = False,
                    init         = False,
                    clean        = False,
                    skip_checks  = False,
                    checks_first = False,
                    bash_file    = "make.sh",
                    logfile      = None,
                    nolog        = False):
        """Set options for make object

        Kwargs:
            tags (list): List of tags to run
            run_all (bool): TODO
            dryrun (bool): Print commands, do not run
            gen_bash (bool): Generate bash file with commands, do not run
            init (bool): Initialize symlinks
            skip_checks (bool): Skip requested checks
            checks_first (bool): Do requested checks first
            bash_file (str): Custom name for bash file to generate
            logfile (str): Custom name for log file
            nolog (bool): DO not create a log file

        Returns: Sets options internally for make

        """
        self.args                 = {}
        self.args['tags']         = tags
        self.args['run_all']      = run_all
        self.args['dryrun']       = dryrun
        self.args['gen_bash']     = gen_bash
        self.args['init']         = init
        self.args['clean']        = clean
        self.args['skip_checks']  = skip_checks
        self.args['checks_first'] = checks_first
        self.args['bash_file']    = bash_file
        self.args['logfile']      = logfile
        self.args['nolog']        = nolog

    def parse_cli(self):
        """Parse CLI arguments

        Returns: Add 'args' dictionary to 'make' object

        """

        prog   = "make.py"
        desc   = "Run custom Makefile.py"
        parser = argparse.ArgumentParser(prog = prog,
                                         description = desc)
        parser.add_argument('tags',
                            nargs    = '*',
                            type     = str,
                            metavar  = 'TAGS',
                            help     = "Tags to run")
        parser.add_argument('--all',
                            dest     = 'run_all',
                            action   = 'store_true',
                            help     = "Run everything, regardless of tags.",
                            required = False)
        parser.add_argument('-t', '--targets',
                            dest     = 'targets',
                            type     = str,
                            nargs    = '*',
                            metavar  = 'TARGETS',
                            default  = ["."],
                            help     = "Targets (folders) to compile.",
                            required = False)
        parser.add_argument('--dry-run',
                            dest     = 'dryrun',
                            action   = 'store_true',
                            help     = "Print what would run but skip its" +
                                       "execution",
                            required = False)
        parser.add_argument('--gen-bash',
                            dest     = 'gen_bash',
                            action   = 'store_true',
                            help     = "Generate make.sh with what would be" +
                                       "run by --all and skip its execution",
                            required = False)
        parser.add_argument('--init',
                            dest     = 'init',
                            action   = 'store_true',
                            help     = "Symlinks to data, out, tmp",
                            required = False)
        parser.add_argument('--clean',
                            dest     = 'clean',
                            action   = 'store_true',
                            help     = "Clean data (excl. 'raw'), out, tmp",
                            required = False)
        parser.add_argument('--skip-checks',
                            dest     = 'skip_checks',
                            action   = 'store_true',
                            help     = "Skip requested file checks.",
                            required = False)
        parser.add_argument('--checks-first',
                            dest     = 'checks_first',
                            action   = 'store_true',
                            help     = "Check all dependencies at the start.",
                            required = False)
        parser.add_argument('--bash-file',
                            dest     = 'bash_file',
                            type     = str,
                            metavar  = 'BASH_FILE',
                            default  = "make.sh",
                            help     = "Bash file",
                            required = False)
        parser.add_argument('--logfile',
                            dest     = 'logfile',
                            type     = str,
                            metavar  = 'LOGFILE',
                            default  = None,
                            help     = "Log file",
                            required = False)
        parser.add_argument('--nolog',
                            dest     = 'nolog',
                            action   = 'store_true',
                            help     = "Do not create a log file.",
                            required = False)
        parser.add_argument('-v', '--version',
                            action   = 'version',
                            version  = '0.1',
                            help     = "Show current version")
        self.args = vars(parser.parse_args())

    def start_logging(self):
        """Start logger (capture everything to a log)

        Returns: Prints everything to log!

        """
        if self.args['logfile'] is None:
            logfile = path.splitext(sys.argv[0])[0] + '.log'
            logfile = path.join(getcwd(), path.basename(logfile))
        else:
            logfile = path.join(getcwd(), self.args['logfile'])

        if not self.args['nolog']:
            sys.stdout     = Logger(logfile = logfile)
            self.loghandle = sys.stdout.log
            self.log       = AppendLogger(self.loghandle)

    def check_targets(self):
        """Check each target exist and has a Makefile.py

        Depends: Run after parse_cli
        Returns: Adds 'targets' list to make object

        """

        for target in self.args['targets']:
            if not path.isdir(target):
                print("Target '{0}' is not a directory.".format(target))
                sys.exit(-1)

            Makefile = path.join(target, 'Makefile.py')
            if not path.isfile(Makefile):
                print("No 'Makefile.py' found in '{0}'".format(target))
                sys.exit(-1)

        print("Targets look OK. Will try to run.")
        self.targets = self.args['targets']

    def run_targets(self):
        """Run tags from targets passed to args

        Returns: Run Makefile.py in each target

        """

        msg_dryrun   = "THIS IS A DRY RUN! Nothing should execute."
        msg_gen_bash = 'This only generates "{0}"! Nothing should execute.'

        msg_Makefile_ok   = "Running code as specified in '{0}'"
        msg_Makefile_fail = "Makefile.py import for '{0}' failed"

        if self.args['dryrun']:
            print(msg_dryrun)

        self.ntargs = len(self.targets)
        tabs = '' if self.ntargs == 1 else '\t'

        if self.ntargs > 1:
            self.timer('all-start', 'Start')

        for target in self.targets:
            # Clear objects to use
            todo = None
            self.Makefile_objects = {}

            # Files names to use in loop
            bash_file = path.join(target, self.args["bash_file"])
            Makefile  = path.join(target, "Makefile.py")

            # Init messages if dryrun, gen_bash requested
            if self.args['gen_bash'] and not self.args['dryrun']:
                print(msg_gen_bash.format(self.args['bash_file']))
                with open(bash_file, "w+") as bf:
                    bf.write("#!/bin/bash" + 2 * linesep)

            # Import Makefile.py
            # try:  # Python 2
            #     execfile(Makefile, self.Makefile_objects)
            # except:  # Python 3
            #     exec(open(Makefile, "rb").read(), self.Makefile_objects)
            try:
                execfile(Makefile, self.Makefile_objects)
            except Warning as warn:
                msg  = "'{0}' raised a warning: {1}" + linesep
                msg += "Execution will continue; "
                msg += "if you meant to stop the execution, use 'exit()'."
                print(msg.format(Makefile, warn))

            # Check import of 'todo' object was successful
            try:
                todo = self.Makefile_objects['todo']
            except:
                raise Warning(msg_Makefile_fail.format(target))

            # Symlinks to lib, data, out, tmp if requested
            if self.args['init'] or self.args['clean']:
                self.init_target(target, todo)
                if self.args['tags'] == [] and self.args['clean']:
                    msg  = "Specify tags explicitly to run after --clean;"
                    msg += " skipping '{0}'".format(Makefile)
                    print(msg)
                    return(0)

            # Run Makefile.py in target
            print(linesep + msg_Makefile_ok.format(Makefile))
            todo.checktags = OrderedDict()
            self.run_Makefile(target, Makefile, todo)

        if self.ntargs > 1:
            self.timer('all-finish', 'Finish')

        self.finish(tabs)

    def run_directly(self, todo):
        """Run given existing todo object

        Returns: Run steps in todo (MakefileTodo) objecct

        """

        msg_dryrun   = "THIS IS A DRY RUN! Nothing should execute."
        msg_gen_bash = 'This only generates "{0}"! Nothing should execute.'
        msg_Makefile_ok = "Running code as specified in '{0}'"

        if self.args['dryrun']:
            print(msg_dryrun)

        # Files names to use in loop
        Makefile  = sys.argv[0]
        target    = path.split(Makefile)[0]
        bash_file = path.join(target, self.args["bash_file"])

        # Init messages if dryrun, gen_bash requested
        if self.args['gen_bash'] and not self.args['dryrun']:
            print(msg_gen_bash.format(self.args['bash_file']))
            with open(bash_file, "w+") as bf:
                bf.write("#!/bin/bash" + 2 * linesep)

        # Symlinks to lib, data, out, tmp if requested
        if self.args['init'] or self.args['clean']:
            self.init_target(target, todo)
            if self.args['tags'] == [] and self.args['clean']:
                msg  = "Specify tags explicitly to run after --clean;"
                msg += " skipping '{0}'".format(Makefile)
                print(msg)
                return(0)

        # Run todo object
        if todo.__class__.__name__ != 'MakefileTodo':
            raise Warning("todo object is not of class MakefileTodo.")

        print(linesep + msg_Makefile_ok.format(Makefile))
        todo.checktags = OrderedDict()
        self.run_Makefile(target, Makefile, todo)

        self.ntargs = 1
        self.finish('')

    def init_target(self, target, todo):
        """Create lib, data, out, and tmp relative symlinks

        Args:
            target (str): Path to target
            todo (MakefileTodo): Container with things to do

        Returns: Creates relative symlinks in target

        """

        dryrun    = self.args['dryrun']
        bash_file = self.args["bash_file"]
        defroot   = todo.default.root
        clean     = self.args['clean']

        guess_full = path.abspath(target)
        guess_root, targ = path.split(guess_full)
        guess_root, base = path.split(guess_root)
        # guess_sub  = '-'.join([base, targ]).strip()
        guess_sub  = targ

        guess_out  = path.join(defroot, 'out',  guess_sub)
        guess_tmp  = path.join(defroot, 'tmp',  guess_sub)
        guess_data = path.join(defroot, 'data', guess_sub)

        execstr_out  = 'symlink "{0}" out'.format(guess_out)
        execstr_tmp  = 'symlink "{0}" tmp'.format(guess_tmp)
        execstr_data = 'symlink "{0}" data'.format(guess_data)

        print("Initializing '{0}'".format(target))
        print("\t" + execstr_out)
        print("\t" + execstr_tmp)
        print("\t" + execstr_data)
        if clean:
            print("Cleaning prior output")
            print("\trm -rf out/*")
            print("\trm -rf tmp/*")
            print("\trm -rf data/* # except 'data/raw/'")

        if dryrun:
            print(linesep + '\tcd "{0}"'.format(guess_full))

            print('\tmkdir -p "{0}"'.format(guess_out))
            print('\tmkdir -p "{0}"'.format(guess_tmp))
            print('\tmkdir -p "{0}"'.format(guess_data))

            print('\tln -sf "{0}" out'.format(guess_out))
            print('\tln -sf "{0}" tmp'.format(guess_tmp))
            print('\tln -sf "{0}" data'.format(guess_data))

            if clean:
                print('\trm -rf "out/*"')
                print('\trm -rf "tmp/*"')
                print('\tfor f in `ls data/`; do')
                print('\t\tif [[ "$f" != "raw" ]]; then')
                print('\t\t\trm -rf "$f"')
                print('\t\tfi')
                print('\tdone')

            print('\tcd -' + linesep)
        else:
            wd = getcwd()
            chdir(guess_full)

            if self.args["gen_bash"]:
                with open(bash_file, "a+") as bf:
                    bf.write('cd "{0}"'.format(guess_full) + linesep)

                    bf.write('mkdir -p "{0}"'.format(guess_out) + linesep)
                    bf.write('mkdir -p "{0}"'.format(guess_tmp) + linesep)
                    bf.write('mkdir -p "{0}"'.format(guess_data) + linesep)

                    bf.write('ln -sf "{0}" out'.format(guess_out) + linesep)
                    bf.write('ln -sf "{0}" tmp'.format(guess_tmp) + linesep)
                    bf.write('ln -sf "{0}" data'.format(guess_data) + linesep)

                    if clean:
                        bf.write('for f in `ls data/`; do' + linesep)
                        bf.write('\tif [[ "$f" != "raw" ]]; then' + linesep)
                        bf.write('\t\trm -rf "$f"' + linesep)
                        bf.write('\tfi' + linesep)
                        bf.write('done' + linesep)

                    bf.write('cd -')
                    bf.write(linesep)

                chdir(wd)
                return(0)
            else:
                makedirs_safe(guess_out)
                makedirs_safe(guess_tmp)
                makedirs_safe(guess_data)

                symlink_replace(guess_out, 'out')
                symlink_replace(guess_tmp, 'tmp')
                symlink_replace(guess_data, 'data')

                if clean:
                    for c in ["out", "tmp", "data"]:
                        for f in listdir(c):
                            israw = (f == 'raw')
                            cf = path.join(c, f)
                            fl = path.isfile(cf) or path.islink(cf)
                            if fl and not israw:
                                unlink(cf)
                            elif path.isdir(cf) and not israw:
                                rmtree(cf)

                chdir(wd)
                return(0)

    def run_Makefile(self, target, Makefile, todo):
        """Run 'check', 'get', 'run', and 'sendmail' in Makefile from todo

        Args:
            target (str): Relative path to target
            Makefile (str): Relative path to Makefile
            todo (MakefileTodo): Container with things to do

        Returns: Run the contents of Makefile

        """

        bash_file = self.args['bash_file']
        gen_bash  = self.args['gen_bash']
        dryrun    = self.args['dryrun']
        run_all   = self.args['run_all']
        tags      = self.args['tags'] if self.args['tags'] != [] else ["all"]
        mfname    = path.split(Makefile)[-1]
        fullpath  = path.abspath(target)

        self.timer(target, "\tStarted run for '{0}'".format(target))
        self.load_defaults(todo, fullpath)

        # Check if there is anything to do
        # --------------------------------

        anything = gen_bash or run_all
        for tag in self.checktags:
            anything = anything or tag in tags

        for tag in self.othertags:
            anything = anything or tag in tags

        if not anything:
            self.checktags.sort()
            msg  = ["Nothing to run for target '{0}'".format(target)]
            msg += ["Requested: {0}".format(', '.join(tags))]
            msg += ["In {0}: {1}".format(mfname, ', '.join(self.checktags))]
            print((linesep + '\t').join(msg))
            return(0)

        # Run the things
        # --------------

        # print(target)
        # print(Makefile)
        # for key in todo.check.keys():
        #     check = todo.check[key]
        #     print("Check '{0}'".format(key))
        #     for dkey in check.keys():
        #         print("\t{0}: {1}".format(dkey, check[dkey]))
        #
        # for key in todo.get.keys():
        #     get = todo.get[key]
        #     print("get '{0}'".format(key))
        #     for dkey in get.keys():
        #         print("\t{0}: {1}".format(dkey, get[dkey]))
        #
        # for key in todo.run.keys():
        #     run = todo.run[key]
        #     print("run '{0}'".format(key))
        #     for dkey in run.keys():
        #         print("\t{0}: {1}".format(dkey, run[dkey]))
        #
        # for key in todo.sendmail.keys():
        #     sendmail = todo.sendmail[key]
        #     print("sendmail '{0}'".format(key))
        #     for dkey in sendmail.keys():
        #         print("\t{0}: {1}".format(dkey, sendmail[dkey]))

        self.check_first(todo, fullpath)

        print('\tcd "{0}"'.format(fullpath))
        if gen_bash and not dryrun:
            with open(path.join(fullpath, bash_file), "a+") as bf:
                bf.write('cd "{0}"'.format(fullpath))
                bf.write(linesep)

        # Ensure steps are run in order (but bundle similar steps)
        for loop in todo.loop:
            if loop in ["sync"]:
                self.loop_sync(todo, fullpath)
            elif loop in ["get"]:
                self.loop_get(todo, fullpath)
            elif loop in ["run"]:
                self.loop_run(todo, fullpath, target)
            elif loop is not None:
                msg  = "Malformed loop list; "
                msg += "found '{0}' but expected one of: sync, get, run"
                raise Warning(msg.format(loop))

        print("\tcd -")
        if gen_bash and not dryrun:
            with open(path.join(fullpath, bash_file), "a+") as bf:
                bf.write("cd -")
                bf.write(linesep)

        self.timer(target, "\tFinished run for '{0}'".format(target))

        self.loop_mail(todo, fullpath, target, Makefile)

    def load_defaults(self, todo, fullpath):
        """Load defaults; add checktags with all tags requested by 'get', 'run'

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder

        Returns:
            - Loads default keys into 'todo'
            - Checks the arguments passed were known
            - Creates todo.checktags for tags to check

        """
        get = todo.default.get
        run = todo.default.run
        checktags = []
        othertags = []

        # Load e-mail and sync tags
        # -------------------------

        for key in todo.sendmail:
            othertags += todo.sendmail[key]['tags']

        for key in todo.sync:
            othertags += todo.sync[key]['tags']

        self.othertags = uniquelist(othertags)

        # Load defaults for 'get'
        # -----------------------

        for key in todo.get:
            # Check the requested options are known
            for gkey in todo.get[key].keys():
                if gkey not in ['src', 'dest'] and gkey not in get.keys():
                    msg  = "WARNING: Ignoring unknown argument '{0}' for"
                    msg += " add_get()" + linesep + "Valid arguments = {1}"
                    print(msg.format(gkey, (', '.join(get.keys()))))

            # Load defaults
            for dkey in get.keys():
                if dkey not in todo.get[key].keys():
                    todo.get[key][dkey] = get[dkey]

            # Force tags into a list
            todo.get[key]['tags'] = todo.get[key]['tags']

            checktags += todo.get[key]['tags']

        # Load defaults for 'run'
        # -----------------------

        for key in todo.run:
            # Check the requested options are known
            for rkey in todo.run[key].keys():
                if rkey not in ['file'] and rkey not in run.keys():
                    msg  = "WARNING: Ignoring unknown argument '{0}' for"
                    msg += " add_run()" + linesep + "Valid arguments = {1}"
                    print(msg.format(rkey, (', '.join(run.keys()))))

            # Load defaults
            for dkey in run.keys():
                if dkey not in todo.run[key].keys():
                    todo.run[key][dkey] = run[dkey]

            # Check minimal setup
            if todo.run[key]['exec'] is None:
                todo.run[key]['exec'] = todo.run[key]['executable']

            # If exec or executable were not specified, check if rule is known
            if todo.run[key]['rules'] is not None:
                rule    = uniquelist(todo.run[key]['rules'])
                rules   = list(todo.rules.keys())
                msg_add = "and rules '{0}' not known (known rules: {1})."
                msg_add = msg_add.format(', '.join(rule), ', '.join(rules))
                exists  = False
                for r in rule:
                    exists = exists or r in rules
            elif todo.default.guessrules:
                ext     = path.splitext(todo.run[key]['file'])[-1]
                exists  = ext in todo.extensions.keys()
                msg_add = "and extension '{0}' is not known.".format(ext)
            else:
                exists  = False
                msg_add = "and no rules specified."

            # If no rule or no executable, exit with error
            if todo.run[key]['exec'] is None:
                if not exists:
                    msg = "Missing argument 'executable' in add_run() "
                    raise Warning(msg + msg_add)

            # Force tags into a list
            todo.run[key]['tags'] = todo.run[key]['tags']

            checktags += todo.run[key]['tags']

        self.checktags = uniquelist(checktags)

    def check_first(self, todo, fullpath):
        """Checks files given checktags if --check-first was asked

        Will print to bash_file if requested.

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder

        Returns: Check if files in 'check' exist if check_first was requested
        """
        check       = todo.check
        gen_bash    = self.args['gen_bash']
        run_all     = self.args['run_all']
        dryrun      = self.args['dryrun']
        tags        = self.args['tags'] if self.args['tags'] != [] else ["all"]
        skip_checks = self.args['skip_checks']
        bash_file   = self.args["bash_file"]
        checknow    = self.args['checks_first'] and not skip_checks

        # 'anything' notes if anything should be done. It is true if:
        #      - Flag --all was passed
        #      - Flag --gen-bash was passed
        #      - An existing tag was requested
        anything = gen_bash or run_all
        for tag in self.checktags:
            anything = anything or tag in tags

        # Group each file to check with the same tag. So if a check has
        # tags ["all", "check"] they will be put into checktags["all"]
        # and into checktags["check"]
        for key in check:
            for tag in check[key]['tags']:
                if tag not in todo.checktags.keys():
                    todo.checktags[tag] = []

                todo.checktags[tag] += [check[key]['file']]

            # Force tags into a list
            check[key]['tags'] = uniquelist(check[key]['tags'])

        # Check the files now if
        #     - Requested checks first and not skipped checks OR passed
        #       --gen-bash (will print summary of checks to bash file)
        #     - AND anything to do
        #     - AND this is not a dry run
        if (checknow or gen_bash) and anything:
            if dryrun:
                print("\tDry run. Did NOT check dependencies.")
            else:
                print("\tChecking dependencies:")

            wd = getcwd()
            chdir(fullpath)

            for key in check:
                cfile   = path.abspath(check[key]['file'])
                exists  = path.isdir(cfile) or path.isfile(cfile)
                ctags   = check[key]['tags']

                # Check file if 'all' (default) or if tag in any of the
                # tags requested by 'get' or 'run'
                checkit = "all" in ctags or run_all
                for tag in self.checktags:
                    checkit = checkit or tag in ctags

                # If dry-run, print to log and continue. OR:
                # a) If check and --gen-bash then print to bash
                # b) If not found then raise warning and exit
                # c) If found, note in log and continue
                if checkit:
                    if dryrun:
                        print("\t\tCheck if exists: '{0}'".format(cfile))
                    elif gen_bash:
                        with open(bash_file, "a+") as bf:
                            msg = '# Check if exists (for {0} only): "{1}"'
                            rel = ', '.join(ctags)
                            bf.write(msg.format(rel, cfile) + linesep)
                    elif not skip_checks:
                        if exists:
                            print("\t\tFound '{0}'".format(cfile))
                        else:
                            msg  = linesep + "\t\t"
                            msg += "Could not find '{0}'".format(cfile)
                            msg += linesep + "\t\t"
                            msg += "Asked for: {0}".format(', '.join(ctags))
                            raise OSError(msg)

            chdir(wd)

        if gen_bash and not dryrun:
            with open(path.join(fullpath, bash_file), "a+") as bf:
                bf.write(linesep)

    def loop_sync(self, todo, fullpath):
        """Loop through all the sync files

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder

        Returns: Syncs requested files/folders using rsync

        """
        run_all   = self.args['run_all']
        dryrun    = self.args['dryrun']
        tags      = self.args['tags'] if self.args['tags'] != [] else ["all"]
        checkit   = not self.args['checks_first']
        checkit   = checkit and not self.args['skip_checks']
        bash_file = self.args["bash_file"]
        gen_bash  = self.args['gen_bash']

        for key in todo.sync:
            sync = todo.sync[key]

            # Ignore if tag not in tags
            keep = run_all
            for tag in sync['tags']:
                keep = keep or tag in tags

            # Skip unless gen_bash, in which case all are printed to bash_file
            if not keep and not gen_bash:
                continue

            # Sync source to destination
            skeys   = sync.keys()
            src     = sync['source']
            dest    = sync['dest']
            flags   = sync['flags']
            exclude = sync['exclude']
            partial = sync['partial']
            server  = sync['server']
            sport   = sync['port'] if 'port' in skeys else 22
            suser   = sync['user'] if 'user' in skeys else None
            sname   = sync['server_name'] if 'server_name' in skeys else None
            sfrom   = 'server_from' in skeys
            sto     = 'server_to' in skeys
            prepend = suser is not None and sname is not None

            # Add user@server: to source or dest if requested
            if prepend:
                if sto:
                    dest = ('{0}@{1}:' + dest).format(suser, sname)

                if sfrom:
                    src  = ('{0}@{1}:' + src).format(suser, sname)

            # Add SSH flag to sync to/from server
            if server:
                flags += ' -e "ssh -p {0}" '.format(sport)

            # Exclude what was requested to be excluded
            if exclude is not None:
                for ex in exclude:
                    flags += " --exclude='{0}' ".format(ex)

            execbase = 'rsync {0} '.format(flags)
            if partial is None:
                execlist = [execbase + ' "{0}" "{1}"'.format(src, dest)]
            else:
                execlist = []
                for psrc in partial.keys():
                    pdest = path.join(dest, partial[psrc])
                    psrc  = path.join(src, psrc)
                    execlist += [execbase + ' "{0}" "{1}"'.format(psrc, pdest)]

            # Loop through folders to sync
            for execstr in execlist:
                wd = getcwd()
                chdir(fullpath)

                print("\t" + execstr.strip())
                if dryrun:
                    continue

                if gen_bash:
                    with open(bash_file, "a+") as bf:
                        bf.write(execstr)
                        bf.write(linesep)

                    chdir(wd)
                    continue

                # Check if the source file exists
                # if not path.isfile(path_src) and not path.isdir(path_src):
                #     msg = "'{0}' not found."
                #     raise OSError(msg.format(path_src))

                # Sync source to dest
                system(execstr)
                chdir(wd)

    def loop_get(self, todo, fullpath):
        """Loop through all the files to get

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder

        Returns: Symlinks to all files specified by add_get

        """
        run_all   = self.args['run_all']
        dryrun    = self.args['dryrun']
        tags      = self.args['tags'] if self.args['tags'] != [] else ["all"]
        checkit   = not self.args['checks_first']
        checkit   = checkit and not self.args['skip_checks']
        bash_file = self.args["bash_file"]
        gen_bash  = self.args['gen_bash']

        for key in todo.get:
            get = todo.get[key]

            # Ignore if tag not in tags
            keep = run_all
            for tag in get['tags']:
                keep = keep or tag in tags

            # Skip unless gen_bash, in which case all are printed to bash_file
            if not keep and not gen_bash:
                continue

            # TODO: Ideas for the future // 2017-02-19 20:42 EST
            #     - Options to get specific tag or revision
            #     - Options to get pathstype
            #     - Options to force copy instead of symlink?
            #     - path_src = path.join(path.abspath(target), key)
            #     - path_out = path.join(path.abspath(get['out']))
            #     - path_src = path.join(target, key)

            # symlink from the source to the destination
            path_src  = get['src']
            path_dest = get['dest']
            path_copy = get['copy']
            if path_copy:
                execstr   = 'cp -r "{0}" "{1}"'.format(path_src, path_dest)
            else:
                execstr   = 'ln -sf "{0}" "{1}"'.format(path_src, path_dest)

            print("\t" + execstr.strip())
            if dryrun:
                continue

            wd = getcwd()
            chdir(fullpath)

            if gen_bash:
                with open(bash_file, "a+") as bf:
                    bf.write(execstr)
                    bf.write(linesep)

                chdir(wd)
                continue

            # If not already checked by check_first, check files now if
            # they were tagged for any of the tags in 'get'
            # TODO: Decide if check files for 'get' // 2017-02-20 02:55 EST
            # if checkit:
            #     for gtag in get['tags']:
            #         if gtag in todo.checktags.keys():
            #             mtag = "\t\tRelevant tag: {0}".format(gtag)
            #             for cfile in todo.checktags[gtag]:
            #                 mfile = "\t\tCould not find '{0}'".format(cfile)
            #                 ok    = path.isdir(cfile) or path.isfile(cfile)
            #                 if not ok:
            #                     raise OSError(mfile + linesep + mtag)
            #                 else:
            #                     print("\t\tFound '{0}'".format(cfile))

            # Check if the source file exists
            # NOTE! This is important if the symlink is not relative.
            # if not path.isfile(path_src) and not path.isdir(path_src):
            #     msg = "'{0}' not found."
            #     raise OSError(msg.format(path_src))

            # Create symlink; if already a symlink then replace; if a
            # file or folder then exit with error
            base_dest = path.dirname(path_dest)
            if base_dest != "":
                makedirs_safe(base_dest)

            if path_copy:
                copy2(path_src, path_dest)
            else:
                symlink_replace(path_src, path_dest)

            chdir(wd)

    def loop_run(self, todo, fullpath, target):
        """Executes all the scripts requested by add_run

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder

        Returns: Executes scripts requested by add_run

        """
        run_all   = self.args['run_all']
        dryrun    = self.args['dryrun']
        tags      = self.args['tags'] if self.args['tags'] != [] else ["all"]
        checkit   = not self.args['checks_first']
        checkit   = checkit and not self.args['skip_checks']
        bash_file = self.args["bash_file"]
        gen_bash  = self.args['gen_bash']
        nolog     = self.args['nolog']

        for key in todo.run:
            run   = todo.run[key]
            opts  = run['options']
            args  = run['args']
            rfile = run['file']
            oext  = run['oext']
            executable  = run['exec']
            fname, fext = path.splitext(rfile)

            # Ignore if tag not in tags
            keep = run_all
            for tag in run['tags']:
                keep = keep or tag in tags

            # Skip unless gen_bash, in which case all are printed to bash_file
            if not keep and not gen_bash:
                continue

            # Parse all the things to run
            # ---------------------------

            dext   = todo.extensions
            drules = todo.rules
            torun  = []

            # TODO: path to rules.conf? // 2017-02-19 20:42 EST
            if executable is None:
                # If no exec, rules must be specified
                if run['rules'] is None:
                    # If no rules, try to guess
                    if todo.default.guessrules:
                        # Add rule for known extension
                        if fext in dext.keys():
                            # Extension may specify several rules
                            for rule in dext[fext].keys():
                                kwargs = dext[fext][rule]
                                kwargs['args'] = args
                                kwargs['opts'] = opts
                                attr   = rule + 'Parse'
                                if attr in dir(todo.parse):
                                    parse  = getattr(todo.parse, attr)
                                    torun += parse(rfile, **kwargs)
                                else:
                                    if opts is None:
                                        dopts = todo.rules[rule]['options']
                                    else:
                                        dopts = opts

                                    dexec  = todo.rules[rule]['executable']
                                    dtuple = (dexec, dopts, rfile, args)
                                    dstr   = '{0} {1} "{2}" {3}'
                                    torun += [dstr.format(*dtuple)]
                        else:
                            msg  = "Nothing to do:"
                            msg += " No executable,"
                            msg += " no rules,"
                            msg += " extension '{0}' not known."
                            raise Warning(msg.format(fext))
                    else:
                        msg  = "Nothing to do:"
                        msg += " No executable,"
                        msg += " no rules,"
                        msg += " guessrules set to False."
                        raise Warning(msg)
                else:
                    # Check rules are known
                    unknown = False
                    norules = []
                    for rule in flatten([run['rules']]):
                        if rule not in drules.keys():
                            unknown  = True
                            norules += [rule]

                    if unknown:
                        msg  = "Requested rules '{0}'"
                        msg += " for file '{1}' not known"
                        raise Warning(msg.format(', '.join(norules), rfile))
                    else:
                        for rule in flatten([run['rules']]):
                            attr = rule + 'Parse'
                            if attr in dir(todo.parse):
                                parse = getattr(todo.parse, attr)
                                if run['rules_kwargs'] is not None:
                                    kwargs = run['rules_kwargs']
                                elif 'kwargs' in todo.rules[rule].keys():
                                    kwargs = todo.rules[rule]['kwargs']
                                else:
                                    kwargs = {}

                                kwargs['args'] = args
                                kwargs['opts'] = opts
                                torun += parse(rfile, **kwargs)
                            else:
                                if opts is None:
                                    dopts = todo.rules[rule]['options']
                                else:
                                    dopts = opts

                                dexec  = todo.rules[rule]['executable']
                                dtuple = (dexec, dopts, rfile, args)
                                dstr   = '{0} {1} "{2}" {3}'
                                torun += [dstr.format(*dtuple)]
            else:
                # If executable was specified, parse user-provided options
                opts = "" if opts is None else opts
                for prog in flatten([executable]):
                    dstr   = '{0} {1} "{2}" {3}'
                    torun += [dstr.format(prog, opts, rfile, args)]

            # Run the things!
            # ---------------

            self.timer(target, "\t\tRunning '{0}'".format(rfile))
            for execstr in torun:
                print("\t" + execstr)
                if dryrun:
                    continue

                wd = getcwd()
                chdir(fullpath)

                if gen_bash:
                    with open(bash_file, "a+") as bf:
                        bf.write(execstr)
                        bf.write(linesep)

                    chdir(wd)
                    continue

                # Check relevant files now if not checked first
                if checkit:
                    for rtag in run['tags']:
                        if rtag in todo.checktags.keys():
                            mtag = "\t\tRelevant tag: {0}".format(rtag)
                            for cfile in todo.checktags[rtag]:
                                mfile = "\t\tCannot find '{0}'".format(cfile)
                                msg   = mfile + linesep + mtag
                                ok    = path.isdir(cfile) or path.isfile(cfile)
                                if not ok:
                                    raise OSError(msg)
                                else:
                                    print("\t\tFound '{0}'".format(cfile))

                # Run and try to get exit status from program
                status = system(execstr)

                # Try to cat the file log
                if not nolog:
                    for ext in oext:
                        assumed_log = fname + ext
                        if path.isfile(assumed_log):
                            self.log.append(assumed_log, execstr)
                            unlink(assumed_log)
                        else:
                            msg = "\tWARNING: Could not attach '{0}'"
                            print(msg.format(assumed_log))

                if status != 0:
                    msg = "Non-0 exit status for `{0}`"
                    raise Warning(msg.format(execstr))

                chdir(wd)

    def loop_mail(self, todo, fullpath, target, Makefile):
        """Send e-mails if required

        Args:
            todo (MakefileTodo): Object containing what to do
            fullpath (str): Full file path of target folder
            target (str): Folder path
            Makefile (str): Path to makefile

        Returns: Sends e-mails to requested recipients

        """
        run_all   = self.args['run_all']
        dryrun    = self.args['dryrun']
        tags      = self.args['tags'] if self.args['tags'] != [] else ["all"]
        bash_file = self.args["bash_file"]
        gen_bash  = self.args['gen_bash']

        msg = "Status: Exited with 0 status (OK) for target '{0}'"
        mail_msg = [msg.format(fullpath)]
        for step in self.timestampts[target].keys():
            dtstr     = self.timestampts[target][step][0]
            mail_msg += ["{0}: {1}".format(step, dtstr)]

        print(linesep + linesep.join(mail_msg))

        # Loop through each e-mail request
        defaultmail = todo.default.sendmail
        for key in todo.sendmail:
            sendmail = todo.sendmail[key]

            # A recipient must be specified
            if todo.default.email is None:
                if 'to' not in sendmail.keys():
                    print("WARNING: Cannot e-mail; no recipients specified.")
                    continue
                elif sendmail['to'] is None:
                    print("WARNING: Cannot e-mail; no recipients specified.")
                    continue
            elif 'to' in sendmail.keys():
                if sendmail['to'] is None:
                    sendmail['to'] = todo.default.email

            # Check the requested options are known
            for skey in sendmail.keys():
                if skey not in defaultmail.keys():
                    msg  = "WARNING: Ignoring unknown argument '{0}' for "
                    msg += "add_sendmail()" + linesep + "Valid arguments = {1}"
                    print(msg.format(skey, (', '.join(defaultmail.keys()))))

            # Load defaults
            for dkey in defaultmail.keys():
                if dkey not in sendmail.keys():
                    sendmail[dkey] = defaultmail[dkey]

            # Ignore if tag not in tags
            keep = run_all
            for tag in sendmail['tags']:
                keep = keep or tag in tags

            if not keep and not gen_bash:
                continue

            mail_to   = sendmail['to']
            mail_sub  = "make.py ran {0} [Automated Message]".format(Makefile)
            mail_prog = 'echo "{0}" | mail -s "{1}" {2}'

            msg  = "Status: Exited with 0 status (OK) for target '{0}'"
            emsg = mail_prog.format(linesep.join(mail_msg), mail_sub, mail_to)
            smsg = mail_prog.format(msg.format(fullpath), mail_sub, mail_to)
            if gen_bash:
                with open(path.join(fullpath, bash_file), "a+") as bf:
                    bf.write(smsg + linesep)
                    bf.write(linesep)
            elif not dryrun:
                # TODO: Attachments! // 2017-02-19 22:49 EST
                if sendmail['attachments'] is not None:
                    for att in sendmail['attachments']:
                        if not path.isdir(target):
                            msg = "WARNING: '{0}' not found. Will NOT attach."
                            print(msg.format(att))

                # If AUTO, send simple message
                if key == 'AUTO':
                    system(emsg)

    def finish(self, tabs):
        """Print ending messages

        Returns: Find ending message to console/log

        """
        end_msg  = ["All targets ran with 0 exit status."]
        end_msg += ["\tPath: {0}".format(path.abspath(getcwd()))]
        end_msg += ["\tCall: {0}".format(' '.join(sys.argv))]
        if self.ntargs > 1:
            for targ in self.timestampts.keys():
                for step in self.timestampts[targ].keys():
                    dtstr    = self.timestampts[targ][step][0]
                    end_msg += ["{0}{1}: {2}".format(tabs, step, dtstr)]

        print(linesep + linesep.join(end_msg))


# ---------------------------------------------------------------------
# Aux classes


class MakeRules():

    """Various rules for file execution"""

    def __init__(self):
        """File extension and rules dictionary """

        latex_clean = [
            "{0}.synctex.gz(busy)",
            "{0}.synctex",
            "{0}.synctex.gz",
            "{0}.aux",
            "{0}.log",
            "{0}.lof",
            "{0}.lot",
            "{0}.fls",
            "{0}.out",
            "{0}.toc",
            "{0}.fmt",
            "{0}.fot",
            "{0}.cb",
            "{0}.cb2",
            "{0}.bbl",
            "{0}.bcf",
            "{0}.blg",
            "{0}-blx.aux",
            "{0}-blx.bib",
            "{0}.brf",
            "{0}.run.xml",
            "{0}.fdb_latexmk",
            "{0}.pdfsync",
            "{0}.alg",
            "{0}.loa",
            "{0} amsthm",
            "{0}.thm",
            "{0} beamer",
            "{0}.nav",
            "{0}.snm",
            "{0}.vrb",
            "{0} cprotect",
            "{0}.cpt",
            "{0}.lox",
            "{0}-gnuplottex-*",
            "{0}.brf",
            "{0}-concordance.tex",
            "{0}.tikz",
            "{0}-tikzDictionary",
            "{0}.lol",
            "{0}.idx",
            "{0}.ilg",
            "{0}.ind",
            "{0}.ist",
            "{0}.maf",
            "{0}.mlf",
            "{0}.mlt",
            "{0}.mtc",
            "{0}_minted*",
            "{0}.pyg",
            "{0}.mw",
            "{0}.fmt",
            "{0}.nlo",
            "{0}.sagetex.sage",
            "{0}.sagetex.py",
            "{0}.sagetex.scmd",
            "{0}.sout",
            "{0}.sympy",
            "{0}.upa",
            "{0}.upb",
            "{0}.pytxcode",
            "{0}.dpth",
            "{0}.md5",
            "{0}.auxlock",
            "{0}.tdo",
            "{0}.xdy",
            "{0}.xyc",
            "{0}.ttt",
            "{0}.fff",
            "sympy-plots-for-*.tex",
            "pythontex-files-*",
            "TSWLatexianTemp*"
        ]

        latex_clean = [
            "{0}.synctex.gz(busy)",
            "{0}.synctex",
            "{0}.synctex.gz",
            "{0}.aux",
            "{0}.log",
            "{0}.out",
            "{0}.toc",
            "{0}.lof",
            "{0}.lot",
            "{0}.fls",
            "{0}.fdb_latexmk",
            "{0}.pdfsync"
        ]

        # Initialize
        self.extensions = {
            '.sas': OrderedDict(),
            '.do': OrderedDict(),
            '.R': OrderedDict(),
            '.py': OrderedDict(),
            '.jl': OrderedDict(),
            '.tex': OrderedDict()
        }

        # Options for each rule
        self.extensions['.sas']['sas']   = {}
        self.extensions['.do']['stata']  = {}
        self.extensions['.R']['R']       = {}
        self.extensions['.py']['python'] = {}
        self.extensions['.jl']['julia']  = {}
        self.extensions['.tex']['latex'] = {'clean': True,
                                            'bibtex': False,
                                            'extra_compile': 0}

        self.rules = {
            'stata': {
                'executable': "stata-mp",
                'options': "-b do",
            },
            'sas': {
                'executable': "sas",
                'options': "",
            },
            'R': {
                'executable': "R CMD BATCH",
                # 'executable': "Rscript",
                'options': "",
            },
            'python': {
                'executable': "python",
                'options': "",
            },
            'julia': {
                'executable': "julia",
                'options': "",
            },
            'latex': {
                'executable': "xelatex",
                'options': "-synctex=1 -shell-escape",
                'kwargs': {'clean': True,
                           'bibtex': False,
                           'extra_compile': 0},
                'clean': latex_clean
            },
        }

    def latexParse(self, filename,
                   args = '',
                   opts = None,
                   clean = True,
                   bibtex = False,
                   extra_compile = None,
                   pre = ''):
        # if extra_compile is None:
        #     extra_compile = self.rules['latex']['kwargs']['extra_compile']
        # clean      = clean and self.rules['latex']['kwargs']['clean']
        # bibtex     = bibtex and self.rules['latex']['kwargs']['bibtex']
        executable = self.rules['latex']['executable']
        opts       = self.rules['latex']['options'] if opts is None else opts
        executable = self.rules['latex']['executable']
        opts       = self.rules['latex']['options'] if opts is None else opts
        base_file  = path.splitext(filename)[0]
        base_str   = (pre + ' {0} {1} "{2}" {3}').strip()
        base_exec  = base_str.format(executable, opts, filename, args)
        execlist   = [base_exec]
        execlist  += [base_exec]
        if bibtex:
            execlist += ['bibtex "{0}.aux"'.format(base_file)]
            execlist += [base_exec]
            execlist += [base_exec]

        while extra_compile > 0:
            execlist += [base_exec]
            extra_compile -= 1

        if clean:
            for what in self.rules['latex']['clean']:
                execlist += ['rm -rf "{0}"'.format(what.format(base_file))]

        return execlist

    def stataParse(self, filename, args = '', opts = None, pre = ''):
        executable = self.rules['stata']['executable']
        opts       = self.rules['stata']['options'] if opts is None else opts
        base_str   = (pre + ' {0} {1} "{2}" {3}').strip()
        execstr    = base_str.format(executable, opts, filename, args)
        execlist   = [execstr.replace('"', '\\"')]
        return execlist

    def sasParse(self, filename, args = '', opts = None, pre = ''):
        executable = self.rules['sas']['executable']
        opts       = self.rules['sas']['options'] if opts is None else opts
        base_str   = pre + ' {0} {1} "{2}" {3}'
        execlist   = [base_str.format(executable, opts, filename, args)]
        return execlist

    def RParse(self, filename, args = '', opts = None, pre = ''):
        executable = self.rules['R']['executable']
        opts       = self.rules['R']['options'] if opts is None else opts
        base_str   = (pre + ' {0} {1} "{2}" {3}').strip()
        execlist   = [base_str.format(executable, opts, filename, args)]
        return execlist

    def pythonParse(self, filename, args = '', opts = None, pre = ''):
        executable = self.rules['python']['executable']
        opts       = self.rules['python']['options'] if opts is None else opts
        base_str   = (pre + ' {0} {1} "{2}" {3}').strip()
        execlist   = [base_str.format(executable, opts, filename, args)]
        return execlist

    def juliaParse(self, filename, args = '', opts = None, pre = ''):
        executable = self.rules['julia']['executable']
        opts       = self.rules['julia']['options'] if opts is None else opts
        base_str   = (pre + ' {0} {1} "{2}" {3}').strip()
        execlist   = [base_str.format(executable, opts, filename, args)]
        return execlist


class MakefileDefaults():

    """Base object to be used by make.py"""

    def __init__(self):
        """Set defaults"""
        self.email      = None
        self.root       = path.join('..', '..')
        self.pathstype  = None   # Not yet implemented
        self.guessrules = False  # Not yet implemented
        self.revision   = None   # Not yet implemented
        self.git_tag    = None   # Not yet implemented

        self.get = {
            'revision': None,
            'git_tag': None,
            'copy': False,
            'pathstype': ["relative"],
            'tags': ["all"],
        }

        self.run = {
            'executable': None,
            'exec': None,
            'options': None,
            'args': "",
            'oext': [".log"],
            'rules': None,
            'rules_conf': None,
            'rules_kwargs': None,
            'tags': ["all"]
        }

        self.sendmail = {
            'to': None,
            'cc': None,
            'bcc': None,
            'subject': None,
            'body': None,
            'attachments': None,
            'tryusing': ["shell"],
            'tags': ["all"]
        }

        self.sync = {
            'exclude': None,
            'partial': None,
            'server': None,
            'flags': "-arlhvv --progress --update --delete",
            'tags': ["all"]
        }


class MakefileTodo(MakefileDefaults):

    """Makefile functions to add to ordered dicts"""

    def __init__(self):
        """Initialize defaults and ordered dictionaries"""
        self.default      = MakefileDefaults()
        self.check        = OrderedDict()
        self.get          = OrderedDict()
        self.run          = OrderedDict()
        self.sync         = OrderedDict()
        self.sendmail     = OrderedDict()
        self.counter      = 0

        self.parse      = MakeRules()
        self.extensions = self.parse.extensions
        self.rules      = self.parse.rules
        self.loop       = [None]

    def add_check(self, filename, tags = ["all"], **kwargs):
        """Add filenames whose existence you will check

        Args:
            filename (str): File name to check exists
            **kwargs: Other arguments to pass to 'check' dict

        Kwargs:
            tags (list): Tags; will check if any tag in tags is requested

        Returns: Adds entry 'filename' to 'check' dictionary.

        """
        tags = uniquelist([tags, "check"])
        self.check[self.counter] = {'file': filename, 'tags': tags}
        for key in kwargs.keys():
            self.check[self.counter][key] = kwargs[key]

        self.counter += 1

    def add_get(self, source, dest, copy = False, tags = ["all"], **kwargs):
        """Will 'get' (symlink) file from source to dest

        This feature is experimental and typically not used.

        Args:
            source (str): File source
            dest (str): Symlink destrination
            **kwargs: Other arguments to pass to 'get' dict

        Kwargs:
            tags (list): Tags; will check if any tag in tags is requested

        Returns: Adds entry to 'get' dictionary.

        """
        tags = uniquelist([tags, "get"])
        self.get[self.counter] = {
            'src': source,
            'dest': dest,
            'copy': copy,
            'tags': tags
        }

        for key in kwargs.keys():
            self.get[self.counter][key] = kwargs[key]

        self.loop    += ["get"] if self.loop[-1] != "get" else []
        self.counter += 1

    def add_run(self, filename,
                executable = None,
                rules      = None,
                options    = None,
                out_ext    = [".log"],
                args       = "",
                tags       = ["all"],
                **kwargs):
        """Will run each filename in order.

        This will run 'filename' according to a list of known rules
        (possibly by guessing the rule based on the file extension), or

        >>> run = '{} {} "{}" {}'.format(executable, options, filename, args)
        >>> system(run)

        Args:
            filename (str): File to run with 'executable'
            **kwargs: Other arguments to pass to 'run' dict

        Kwargs:
            executable (str): Path to executable. Required if guessrules
                              is set to False or if no rule is specified
            rules (str or list): Rules to apply to 'filename'. If guessrules is
                                 True then rules are based off file extensions.
            options (str): Placed between 'executable' and 'filename'
            out_ext (list): Output extension(s) to append to make.log
            args (str): Placed after 'filename'
            tags (list): Tags; will check if any tag in tags is requested

        Returns: Adds entry to 'run' dictionary.

        """
        tags = uniquelist([tags, filename, "run"])
        if not self.default.guessrules:
            if executable is None and rules is None:
                msg  = "run() missing 1 positional argument"
                msg += "'executable' or 'rules' when default.guessrules"
                msg += "is set to 'False'"
                raise TypeError(msg)

        self.run[self.counter] = {
            'file': filename,
            'executable': executable,
            'exec': executable,
            'options': options,
            'oext': uniquelist(out_ext),
            'args': args,
            'rules': rules,
            'tags': tags
        }

        for key in kwargs.keys():
            self.run[self.counter][key] = kwargs[key]

        self.loop    += ["run"] if self.loop[-1] != "run" else []
        self.counter += 1

    def add_sendmail(self, tags = ["all"], **kwargs):
        """Will send e-mail after runs are compelted

        Args:
            **kwargs: Other arguments to pass to 'sendmail' dict

        Kwargs:
            to (str or list): E-mail(s) to e-mail after runs are done
            tags (list): Tags; will check if any tag in tags is requested

        Returns: Adds entry 'AUTO' to 'sendmail' dictionary.

        """
        tags = uniquelist([tags, "sendmail"])
        if self.default.email is None and 'to' not in kwargs.keys():
            msg  = "sendmail() missing 1 positional argument"
            msg += "'to' when default.email is not set."
            raise TypeError(msg)

        self.sendmail['AUTO'] = {'to': self.default.email, 'tags': tags}
        for key in kwargs.keys():
            self.sendmail['AUTO'][key] = kwargs[key]

    def add_sync(self, source, dest,
                 exclude = None,
                 partial = None,
                 server = False,
                 flags = "-arlhvv --progress --update",
                 delete = False,
                 tags = ["all"],
                 **kwargs):
        """Sync source w/dest, full or partial, optionally excluding files

        This uses rsync to sync files; in case 'server' is specicied,
        then the sync takes place over SSH to the specified server.

        Args:
            source (str): File or folder to sync
            dest (str): Destination file or folder
            **kwargs: Other arguments to pass to 'sync' dict. This is
                used to pass arguments related to syncing to/from a
                server (user, server_name, server_to, server_from, port)

        Kwargs:
            exclude (list): List of names to exclude. Each entry will be
                passed to rsync as "--exclude='{}'"
            partial (dict): Dictionary with partial source/dest files.
                Each key is assumed to be a subfolder or subfile from
                'source' and its value is assumed to be the destrination
                from 'dest'.
            server (bool): Whether to sync to/from server. This just adds
                -e "ssh -p 22" to the rsync function call (where 22 is
                replaced with the value of 'port' when specified).
            flags (str): Flags for rsync
            delete (bool): Add '--delete' flag
            tags (list): Tags; will check if any tag in tags is requested

        Returns: Adds entry to 'sync' dictionary.

        """
        flags += " --delete" if delete else ""
        tags   = uniquelist([tags, "sync"])
        sfrom  = re.match(r".+@.+:(/|\\).+", source)
        sto    = re.match(r".+@.+:(/|\\).+", dest)
        ok     = sfrom or sto
        skeys  = kwargs.keys()

        prepend = 'user' in skeys and 'server_name' in skeys
        to_in   = 'server_to' in skeys
        from_in = 'server_from' in skeys

        if server:
            if not ok:
                if not prepend:
                    msg  = "WARNING: One of source, dest should be a server"
                    msg += " path if 'user' and 'server_name' unspecified."
                    print(msg)
                elif not to_in and not from_in:
                    msg  = "'server_to' or 'server_from' required with"
                    msg += " user, server_name"
                    raise Warning(msg)
                elif to_in and from_in:
                    msg = "Can only sync to or from server, not both"
                    raise Warning(msg)
        else:
            if prepend:
                print("user, server_name ignored unless server = True")

            if to_in:
                print("server_to unless server = True")

            if from_in:
                print("server_to unless server = True")

        self.sync[self.counter] = {
            'source': source,
            'dest': dest,
            'exclude': exclude,
            'partial': partial,
            'server': server,
            'flags': flags,
            'tags': tags
        }

        for key in kwargs.keys():
            self.sync[self.counter][key] = kwargs[key]

        self.loop    += ["sync"] if self.loop[-1] != "sync" else []
        self.counter += 1


class Logger():

    """Hack to output everything to a log"""

    def __init__(self, logfile = None):
        if logfile is None:
            logfile = path.splitext(path.basename(sys.argv[0]))[0] + '.log'

        self.terminal = sys.stdout
        self.log = open(logfile, 'w')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass


class AppendLogger():

    """Append logs to make.log, with markers"""

    def __init__(self, loghandle):
        head  = linesep
        head += '>' + 71 * '>' + linesep
        head += '> Log file: {0}' + linesep
        head += '> Program call: {1}' + linesep
        head += '> Working directory: {2}' + linesep
        head += '>' + 71 * '>' + linesep + linesep

        tail  = linesep + '<' + 71 * '<'
        tail += tail + linesep

        self.loghandle = loghandle
        self.head      = head
        self.tail      = tail

    def append(self, logfile, call):
        headstr = self.head.format(logfile, call, getcwd())
        append  = [headstr] + open(logfile).readlines() + [self.tail]
        for line in append:
            self.loghandle.write(line)

        sleep(1)


# ---------------------------------------------------------------------
# Aux functions

# Backwards-compatible list flattening
# http://stackoverflow.com/questions/2158395/
def flatten(l):
    if version_info >= (3, 0):
        for el in l:
            if isinstance(el, Iter) and not isinstance(el, (str, bytes)):
                for sub in flatten(el):
                    yield sub
            else:
                yield el
    else:
        for el in l:
            if isinstance(el, Iter) and not isinstance(el, basestring):
                for sub in flatten(el):
                    yield sub
            else:
                yield el


# Return a flattened list of unique items
def uniquelist(x):
    return list(set(flatten([x])))


# Recursively make a directory; check if it already exists
def makedirs_safe(directory):
    try:
        makedirs(directory)
        return directory
    except OSError:
        if not path.isdir(directory):
            raise


# Create a symlink; try to replace if file exists
def symlink_replace(src, dest, **kwargs):
    try:
        symlink(src, dest, **kwargs)
        return dest
    except OSError:
        if path.islink(dest):
            try:
                unlink(dest)
                symlink(src, dest, **kwargs)
                return dest
            except OSError:
                raise
        elif path.isfile(dest) or path.isdir(dest):
            print("WARNING: '{0}' exists and is not a symlink.".format(dest))
        else:
            raise


# printf-style printing
def printf(print_format, *args):
    sys.stdout.write(print_format.format(*args))


# Define basestring in a backwards-compatible way
try:  # Python 2
    "" is basestring
except NameError:  # Python 3
    basestring = str


# ---------------------------------------------------------------------
# Run the things!

if __name__ == "__main__":
    main()
