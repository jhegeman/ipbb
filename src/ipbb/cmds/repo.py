
# Modules
import click
import os
import pathlib
import subprocess
import sh
import sys
import yaml

# Elements
from os.path import join, split, exists, splitext, dirname, basename, abspath

from ..console import cprint
from ..defaults import kSourceDir, kProjDir, kWorkAreaFile, kRepoFile
from ..depparser import Pathmaker, DepFormatter, dep_command_types
from ..utils import mkdir
from ..utils import DirSentry, findFileInParents, raiseError, formatDictTable
from .proj import info as proj_info
from urllib.parse import urlparse
from distutils.dir_util import mkpath
from rich.table import Table


# ------------------------------------------------------------------------------
def init(ictx, directory):
    '''Initialise a new firmware development area'''

    cprint(f"Setting up new firmware work area {directory}", style='green')

    if ictx.work.path is not None:
        raise click.ClickException(
            'Cannot create a new work area inside an existing one %s' % ictx.work.path
        )

    if exists(directory) and os.listdir(directory):
        raise click.ClickException('Directory \'%s\' already exists and it\'s not empty' % directory)

    # Build source code directory
    mkpath(join(directory, kSourceDir))
    mkpath(join(directory, kProjDir))

    with open(join(directory, kWorkAreaFile), 'w') as lSignature:
        lSignature.write('\n')


# ------------------------------------------------------------------------------
def info(ictx, verbose):
    '''Print a brief report about the current working area'''

    if not ictx.work.path:
        cprint('ERROR: No ipbb work area detected', style='red')
        return

    cprint()

    lEnvTable = Table('name', 'path', title='ipbb context', title_style='blue', show_header=False)
    lEnvTable.add_row("Work path", ictx.work.path)
    if ictx.currentproj.path:
        lEnvTable.add_row("Project path", ictx.currentproj.path)
    cprint(lEnvTable)

    if not ictx.currentproj.path:
        cprint()
        srcs_info(ictx)

        cprint()
        proj_info(ictx)
        return

    cprint()

    if not ictx.currentproj.settings:
        return

    t = formatDictTable(ictx.currentproj.settings, aHeader=False)
    t.title = "Project '[green]%s[/green]'" % ictx.currentproj.name
    t.title_style = 'blue'
    cprint(t)

    cprint()

    if ictx.currentproj.usersettings:
        cprint("User settings", style='blue')
        t = formatDictTable(ictx.currentproj.usersettings, aHeader=False)
        t.title = "User settings"
        t.title_style = 'blue'
        cprint(t)

        cprint()

    lParser = ictx.depParser
    lDepFmt = DepFormatter(lParser)

    if lParser.errors:
        t = lDepFmt.draw_parsing_errors()
        t.title = "Dep tree parsing error(s)"
        t.title_style = 'red'
        cprint(t)
        
        cprint()

    t = lDepFmt.draw_deptree_commands_summary()
    t.title = "Dependecy tree elements"
    t.title_style = 'blue'
    cprint(t)

    cprint()

    if  lParser.unresolved:
        t = lDepFmt.draw_unresolved_summary()
        t.title = "Unresolved item(s)"
        t.title_style = 'red'
        cprint(t)

        cprint()
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def add(ictx):
    '''Add a new package to the source area'''
    # -------------------------------------------------------------------------
    # Must be in a build area
    if ictx.work.path is None:
        raise click.ClickException('Build area root directory not found')


# ------------------------------------------------------------------------------
def _repo_init(ictx, repo):

    if repo not in ictx.sources:
        cprint('Source package {} not found'.format(repo), style='red')
        cprint('Available repositories:')
        for lPkg in ictx.sources:
            cprint(' - ' + lPkg)

        raiseError("Source package {} not found".format(repo))

    repo_settings = ictx.sources_info[repo].repo_settings
    # _load_repo_settings(srcdir, repo)
    # repo_file_path = join(srcdir, repo, kRepoFile)
    # if not exists(repo_file_path):
    #     cprint('No repository setup file found in {}. Skipping'.format(repo), style='blue')
    #     return
    # cprint('Setting up {}'.format(repo), style='blue')

    # repo_settings = None
    # with open(repo_file_path, 'r') as f:
    #     repo_settings = yaml.safe_load(f)

    init_settings = repo_settings.get('init', None)
    if init_settings is None:
        cprint("No init configuration file. Skipping.")
        return

    cmds = [ l.split() for l in init_settings ]

    # ensure that all commands exist
    missingCmds = [(i, cmd) for i, cmd in enumerate(cmds) if not sh.which(cmd[0])]
    if missingCmds:
        cprint('Some setup commands have not been found', style='red')
        for i, cmd in missingCmds:
            cprint(' - {} (line {})'.format(cmd, i))

        raiseError("Setup commands not found".format(repo))

    with sh.pushd(join(ictx.srcdir, repo)):
        # TODO: add error handling
        # Show the list of commands
        # In green the commands executed successfully
        # In red the failed one
        # In white the remaining commands
        for cmd in cmds:
            cprint('> '+' '.join(cmd), style='cyan')
            sh.Command(cmd[0])(*cmd[1:], _out=sys.stdout)

# ------------------------------------------------------------------------------
def _repo_reset(ictx, repo):

    if repo not in ictx.sources:
        cprint('Source package {} not found'.format(repo), style='red')
        cprint('Available repositories:')
        for lPkg in ictx.sources:
            cprint(' - ' + lPkg)

        raiseError("Source package {} not found".format(repo))

    repo_settings = ictx.sources_info[repo].repo_settings

    # repo_file_path = join(ictx.srcdir, repo, kRepoFile)
    # if not exists(repo_file_path):
    #     cprint('No repository setup file found in {}. Skipping'.format(repo), style='blue')
    #     return
    # cprint('Resetting up {}'.format(repo), style='blue')

    # repo_settings = None
    # with open(repo_file_path, 'r') as f:
    #     repo_settings = yaml.safe_load(f)

    reset_settings = repo_settings.get('reset', None)
    if reset_settings is None:
        cprint("No reset configuration file. Skipping.")
        return

    cmds = [ l.split() for l in reset_settings ]

    # ensure that all commands exist
    missingCmds = [(i, cmd) for i, cmd in enumerate(cmds) if not sh.which(cmd[0])]
    if missingCmds:
        cprint('Some setup commands have not been found', style='red')
        for i, cmd in missingCmds:
            cprint(' - {} (line {})'.format(cmd, i))

        raiseError("Setup commands not found".format(repo))

    with sh.pushd(join(ictx.srcdir, repo)):
        # TODO: add error handling
        # Show the list of commands
        # In green the commands executed successfully
        # In red the failed one
        # In white the remaining commands
        for cmd in cmds:
            cprint('> '+' '.join(cmd), style='cyan')
            sh.Command(cmd[0])(*cmd[1:], _out=sys.stdout)


# ------------------------------------------------------------------------------
def git(ictx, repo, branch_or_tag, revision, dest, depth):
    '''Add a git repository to the source area'''

    cprint('Adding git repository [blue]{}[/blue]'.format(repo))

    # Ensure that the destination direcotry doesn't exist
    # Maybe not necessary

    lUrl = urlparse(repo)
    # Strip '.git' at the end
    lRepoName = splitext(basename(lUrl.path))[0] if dest is None else dest
    lRepoLocalPath = join(ictx.work.path, kSourceDir, lRepoName)

    # Check for
    if exists(lRepoLocalPath):
        raise click.ClickException('Repository already exists \'%s\'' % lRepoLocalPath)

    if branch_or_tag is not None:

        lLsRemoveTags =  sh.git('ls-remote', '-h', '-t', repo, f'refs/tags/{branch_or_tag}')
        lRemoteTagRefs = [
            line.strip().split('\t') for line in lLsRemoveTags.split('\n') if line
        ]

        lLsRemoveBranches =  sh.git('ls-remote', '-h', '-t', repo, f'refs/heads/{branch_or_tag}')
        lRemoteHeadRefs = [
            line.strip().split('\t') for line in lLsRemoveBranches.split('\n') if line
        ]


        lRemoteRefs = lRemoteTagRefs+lRemoteHeadRefs;
        if not lRemoteRefs:
            raise click.ClickException(
                'No references matching \'{}\' found'.format(branch_or_tag)
            )
        elif len(lRemoteRefs) > 1:
            # cprint(lRemoteRefs)
            for h,r in lRemoteRefs:
                cprint(f"- {r}: {h}")
            raise click.ClickException(
                'Found {} references matching \'{}\''.format(len(lRemoteRefs), branch_or_tag)
            )

        if lRemoteTagRefs:
            lRefKind = 'tag'
        elif lRemoteHeadRefs:
            lRefKind = 'branch'


        lRef, lRefName = lRemoteRefs[0]

        # All good, go ahead with cloning
        cprint(
            "{} [blue]{}[/blue] resolved as reference {}".format(
                lRefKind.capitalize(), branch_or_tag, lRefName
            )
        )

    lCloneArgs = ['clone', repo]

    if dest is not None:
        lCloneArgs += [dest]

    if depth is not None:
        lCloneArgs += [f'--depth={depth}']

    # NOTE: The mutual exclusivity of checking out a branch and
    # checkout out a revision should have been handled at the CLI
    # option handling stage.
    if revision is not None:
        sh.git(*lCloneArgs, _out=sys.stdout, _cwd=ictx.srcdir)
        cprint('Checking out revision [blue]{}[/blue]'.format(revision))
        try:
            lFetchArgs = ['fetch', 'origin', revision, '-q']
            if depth is not None:
                lFetchArgs += [f'--depth={depth}']
            sh.git(*lFetchArgs, _out=sys.stdout, _cwd=lRepoLocalPath)
            sh.git('checkout', revision, '-q', _out=sys.stdout, _cwd=lRepoLocalPath)
        except Exception as err:
            # NOTE: The assumption here is that the failed checkout
            # did not alter the state of the cloned repo in any
            # way. (This appears to be the case from experience but no
            # hard reference could be found.)
            cprint("Failed to check out requested revision." \
                  " Staying on default branch.", style='red')
    else:
        if branch_or_tag is None:
            cprint(f'Cloning default branch')
        else:
            lCloneArgs.append(f'--branch={branch_or_tag}')
            cprint(f'Cloning branch/tag [blue]{branch_or_tag}[/blue]')
        sh.git(*lCloneArgs, _out=sys.stdout, _cwd=ictx.srcdir)

    cprint(
        'Repository \'{}\' successfully cloned to:\n  {}'.format(
            lRepoName, join(ictx.srcdir, lRepoName)
        ),
        style='green',
    )

    _repo_init(ictx, lRepoName)


# ------------------------------------------------------------------------------
def svn(ictx, repo, dest, rev, dryrun, sparse):
    '''Add a svn repository REPO to the source area'''

    lUrl = urlparse(repo)
    lRepoName = splitext(basename(lUrl.path))[0] if dest is None else dest
    # -------------------------------------------------------------------------
    # Stop if the target directory already exists
    cprint('Adding svn repository [blue]{}[/blue'.format(repo))

    lRepoLocalPath = join(ictx.srcdir, lRepoName)

    if exists(lRepoLocalPath):
        raise click.ClickException('Repository already exists \'%s\'' % lRepoLocalPath)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    if not sparse:
        lArgs = ['checkout', '-q', repo]

        # Append destination directory if defined
        if dest is not None:
            lArgs.append(dest)

        if rev is not None:
            lArgs += ['-r', str(rev)]

        # Do the checkout
        lCmd = ['svn'] + lArgs
        cprint('Executing [blue]{}[/blue]'.format(' '.join(lCmd)))
        if not dryrun:
            sh.svn(*lArgs, _out=sys.stdout, _cwd=ictx.srcdir)
    else:
        cprint('Sparse checkout mode: [blue]{}[/blue]'.format(sparse))
        # ----------------------------------------------------------------------
        # Checkout an empty base folder
        lArgs = ['checkout', '--depth=empty', repo]

        # Append destination directory if defined
        if dest is not None:
            lArgs.append(dest)

        if rev is not None:
            lArgs += ['-r', str(rev)]

        lCmd = ['svn'] + lArgs
        cprint('Executing [blue]{}[/blue]'.format(' '.join(lCmd)))
        if not dryrun:
            sh.svn(*lArgs, _out=sys.stdout, _cwd=ictx.srcdir)
        # ----------------------------------------------------------------------
        lArgs = ['update']
        lCmd = ['svn'] + lArgs
        for lPath in sparse:
            lTokens = [lToken for lToken in lPath.split('/') if lToken]

            lPartials = ['/'.join(lTokens[: i + 1]) for i, _ in enumerate(lTokens)]

            # Recursively check out intermediate, empty folders
            for lPartial in lPartials:
                lArgs = ['up', '--depth=empty', lPartial]
                cprint('Executing [blue]{}[/blue]'.format(' '.join(['svn'] + lArgs)))
                if not dryrun:
                    sh.svn(*lArgs, _out=sys.stdout, _cwd=lRepoLocalPath)

            # Finally check out the target
            lArgs = ['up', '--set-depth=infinity', lPath]
            cprint('Executing [blue]{}[/blue]'.format(' '.join(['svn'] + lArgs)))
            if not dryrun:
                sh.svn(*lArgs, _out=sys.stdout, _cwd=lRepoLocalPath)

    _repo_init(ictx, lRepoName)

    # -------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def tar(ictx, repo, dest, strip):
    '''Add a tarball-ed package to the source area'''

    cprint("Warning: Command 'untar' is still experimental", style='yellow')
    lProtocols = ['file', 'http', 'https']
    lExtensions = ['.tar', '.tar.gz', '.tgz']

    # -------------------------------------------------------------------------
    # Carefully parse the repository uri
    lUrl = urlparse(repo)

    # Normalize the scheme name
    lUrlScheme = lUrl.scheme if lUrl.scheme else 'file'

    # And check if it is a known protocol
    if lUrl.scheme not in lProtocols:
        raise click.ClickException(
            "Protocol '"
            + lUrl.scheme
            + "'' not supported. Available protocols "
            + ", ".join(["'" + lP + "'" for lP in lProtocols])
        )

    # Normalize the path as well
    lUrlPath = lUrl.path if lUrlScheme != 'file' else join(lUrl.netloc, lUrl.path)

    if not lUrlPath:
        raise click.ClickException('Malformed url: ' + lUrl)

    lMatches = list(filter(lambda lOpt: lUrlPath.endswith(lOpt), lExtensions))
    if not lMatches:
        raise click.ClickException(
            'File format not supported. Supported formats :' + ' '.join(lExtensions)
        )

    lRepoName = basename(lUrlPath).strip(lMatches[0]) if dest is None else dest
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Stop if the target directory already exists
    cprint(
        'Adding tarball [blue]{}[/blue] to [blue]{}[/blue]'.format(repo, lRepoName)
    )
    lRepoLocalPath = join(ictx.work.path, kSourceDir, lRepoName)

    if exists(lRepoLocalPath):
        raise click.ClickException('Repository already exists \'%s\'' % lRepoLocalPath)
    # -------------------------------------------------------------------------

    mkpath(lRepoLocalPath)

    lOptArgs = [] if strip is None else ['--show-transformed', '--strip=' + str(strip)]

    # First case, local file
    if lUrlScheme in ['file']:
        lArgs = ['xvfz', abspath(lUrlPath)] + lOptArgs
        sh.tar(*lArgs, _out=sys.stdout, _cwd=lRepoLocalPath)

    # Second case, remote file
    else:
        lArgs = ['xvz'] + lOptArgs
        sh.tar(sh.curl('-L', repo), *lArgs, _out=sys.stdout, _cwd=lRepoLocalPath)

    _repo_init(ictx, lRepoName)


# ------------------------------------------------------------------------------
def symlink(ictx, path, absolute):

    lRepoName = basename(path)
    lRepoLocalPath = join(ictx.srcdir, lRepoName)

    if exists(lRepoLocalPath):
        raise click.ClickException('Repository already exists \'%s\'' % lRepoLocalPath)

    lPathToCheck = \
        pathlib.Path(abspath(path)) if absolute \
        else pathlib.Path(ictx.srcdir)/path

    if not lPathToCheck.exists():
        raise click.ClickException('Target path \'%s\' does not exist' % lPathToCheck)

    lPathToCreate = \
        lPathToCheck if absolute \
        else path

    cprint(
        'Adding symlink [blue]{}[/blue] to [blue]{}[/blue]'.format(lPathToCreate, lRepoName)
    )

    sh.ln('-s', lPathToCreate, _cwd=ictx.srcdir )


# ------------------------------------------------------------------------------
def srcs(ictx):
    pass

# ------------------------------------------------------------------------------
def _git_info():
    lHEADId, lHash = None, None

    try:
        lBranch = '/'.join(
            sh.git('symbolic-ref', 'HEAD').split('/')[2:]
        ).strip()
    except sh.ErrorReturnCode_128:
        lBranch = None

    try:
        lTag = sh.git(
            'describe', '--tags', '--exact-match', 'HEAD'
        ).strip()   
    except sh.ErrorReturnCode_128:
        lTag = None

    lHash = sh.git('rev-parse', '--short=8', 'HEAD').strip() + '...'

    if lTag is not None:
        lHEADId = lTag
    elif lBranch is not None:
        lHEADId = lBranch
    else:
        lHEADId = lHash

    try:
        sh.git('diff', '--no-ext-diff', '--quiet').strip()
    except sh.ErrorReturnCode_1:
        lHEADId += '*'

    try:
        sh.git('diff', '--no-ext-diff', '--cached', '--quiet').strip()
    except sh.ErrorReturnCode_1:
        lHEADId += '+'

    return lHEADId, lHash


# ------------------------------------------------------------------------------
def _git_submod_info():

    lSubmods = sh.git('submodule', 'status', '--recursive').strip()
    if not lSubmods:
        return []

    lSubmodTokens = [l.strip().split() for l in lSubmods.split('\n')]
    lSubmodInfos = [t[0:2] + [(t[2] if len(t) == 3 else '')] for t in lSubmodTokens]

    return lSubmodInfos


# ------------------------------------------------------------------------------
def _svn_info():
    lHEADId, lHash = None, None

    lSVNInfoRaw = sh.svn('info')

    lSVNInfo = {
        lEntry[0]: lEntry[1].strip()
        for lEntry in (
            lLine.split(':', 1)
            for lLine in lSVNInfoRaw.split('\n')
            if lLine
        )
    }
    
    lHEADId = lSVNInfo['URL'].replace(lSVNInfo['Repository Root'] + '/', '')

    lSVNStatus = sh.svn('status', '-q')
    if len(lSVNStatus):
        lHEADId += '*'

    lHash = lSVNInfo['Revision']

    return lHEADId, lHash

# ------------------------------------------------------------------------------
def srcs_info(ictx):

    if not ictx.work.path:
        cprint('ERROR: No ipbb work area detected', style='red')
        return

    cprint()
    lSrcs = ictx.sources
    if not lSrcs:
        return

    lSrcTable = Table('name', 'kind', 'version', 'hash', title="Firmware Packages", title_style='blue')
    for lSrc in lSrcs:
        lSrcDir = join(ictx.srcdir, lSrc)

        lKind, lHEADId, lHash = "unknown", None, None

        # Check if a git repository
        if exists(join(lSrcDir, '.git')):
            with DirSentry(lSrcDir) as _:

                lKind = 'git'
                try:
                    sh.git('rev-parse', '--git-dir')
                except sh.ErrorReturnCode_128:
                    lSrcTable.add_row(lSrc, lKind+' (broken)', '(unknown)', None)
                    continue

                lHEADId, lHash = _git_info()
                lSrcTable.add_row(lSrc, lKind, lHEADId, lHash)

                lSubmods = sh.git('submodule', 'status', '--recursive').strip()

                for lFullHash, lSubModDir, lDescribe in _git_submod_info():
                    if lFullHash[0] == '-':
                        # Module not initialized
                        lSrcTable.add_row(u'  └──'+basename(lSubModDir), lKind, '-', '-')
                    else:
                        with DirSentry(join(lSrcDir,lSubModDir)) as _:
                            lHEADId, lHash = _git_info()
                            lSrcTable.add_row(u'  └──'+basename(lSubModDir), lKind, lHEADId, lHash)

        elif exists(join(lSrcDir, '.svn')):
            with DirSentry(lSrcDir) as _:
                lKind = 'svn'

                lHEADId, lHash = _svn_info()
                lSrcTable.add_row(lSrc, lKind, lHEADId, lHash)
        else:
            lSrcTable.add_row(lSrc, lKind, lHEADId, lHash)

    cprint(lSrcTable)


# ------------------------------------------------------------------------------
def srcs_create_component(ictx, component):
    lPathMaker = Pathmaker(ictx.srcdir, ictx._verbosity)

    lCmpPath = lPathMaker.getPath(*component)
    if exists(lPathMaker.getPath(*component)):
        cprint("ERROR: Component '{}' already exists".format(lCmpPath), style='red')
        raise click.ClickException("Command aborted")

    for sd in lPathMaker.fpaths:
        lPath = lPathMaker.getPath(*component, command=sd)
        mkdir(lPath)
        cprint("Folder {} created.".format(lPath), style='cyan')


# ------------------------------------------------------------------------------
def srcs_run(ictx, pkg, cmd, args):

    if pkg:
        if pkg not in ictx.sources:
            cprint(
                "ERROR: '{}' package not known.\nKnown packages:\n{}".format(
                    pkg, '\n'.join((' * ' + s for s in ictx.sources))
                ),
                style='red',
            )
            raise click.ClickException("Command failed")
        wd = join(ictx.srcdir, pkg)
    else:
        wd = ictx.srcdir

    try:
        lCmd = sh.Command(cmd)
    except sh.CommandNotFound as lExc:
        cprint("ERROR: Command '{}' not found in path".format(cmd), style='red')
        raise click.ClickException("Command aborted")

    try:
        lCmd(*args, _cwd=wd, _out=sys.stdout, _err=sys.stderr)
    except sh.ErrorReturnCode as lExc:
        raise click.ClickException(
            "Command '{}' failed with error code {}".format(
                lExc.full_cmd, lExc.exit_code
            )
        )


# ------------------------------------------------------------------------------
def srcs_find(ictx):
    sh.find(ictx.srcdir, '-name', '*.vhd', _out=sys.stdout)
