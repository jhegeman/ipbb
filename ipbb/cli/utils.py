from __future__ import print_function
# ------------------------------------------------------------------------------

import os
import ipaddress
import sys
import re

from click import echo, secho, style, confirm, get_current_context, BadParameter
from texttable import Texttable

# ------------------------------------------------------------------------------
class DirSentry:
    def __init__(self, aDir):
        self.dir = aDir

    def __enter__(self):
        if not os.path.exists(self.dir):
            raise RuntimeError('Directory ' + self.dir + ' does not exist')

        self._lOldDir = os.path.realpath(os.getcwd())
        # print self._lOldDir
        os.chdir(self.dir)
        return self

    def __exit__(self, type, value, traceback):
        os.chdir(self._lOldDir)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def findFileDirInParents(aFileName, aDirPath = os.getcwd()):

    lDirPath = aDirPath
    while lDirPath is not '/':
        lBuildFile = os.path.join(lDirPath, aFileName)
        if os.path.exists(lBuildFile):
            return lDirPath
        lDirPath, _ = os.path.split(lDirPath)

    return None
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def findFileInParents(aFileName, aDirPath = os.getcwd()):

    lDirPath = findFileDirInParents(aFileName, aDirPath)

    return join(lDirPath, aFileName) if lDirPath is not None else None
# ------------------------------------------------------------------------------




# ------------------------------------------------------------------------------
def ensureNoMissingFiles(aCurrentProj, aDepFileParser):

    if not aDepFileParser.missing:
        return

    secho("ERROR: Project '{}' contains missing dependencies: {} missing file{}.\n       Run '{} dep report' for details".format(
        aCurrentProj,
        len(aDepFileParser.missing),
        ("" if len(aDepFileParser.missing) == 1 else "s"),
        getClickRootName(),
    ), fg='red')
    confirm("Do you want to continue anyway?", abort=True)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def echoVivadoConsoleError( aExc ):
    echo(
        style("Vivado error/critical warnings detected\n", fg='red')+
        style("\n".join(aExc.errors), fg='red') + '\n' +
        style("\n".join(aExc.criticalWarns), fg='yellow') 
    )

# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def validateComponent(ctx, param, value):
    lSeparators = value.count(':')
    # Validate the format
    if lSeparators != 1:
        raise BadParameter('Malformed component name : %s. Expected <package>:<component>' % value)

    return tuple(value.split(':'))
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def validateIpAddress(value):
    if value is None:
        return

    try:
        lIp = ipaddress.ip_address(value)
    except ValueError as e:
        raise BadParameter, BadParameter(str(e)),  sys.exc_info()[2]

    # import ipdb
    # ipdb.set_trace()
    lHexIp = ''.join([ '%02x' % ord(c) for c in lIp.packed])

    return 'X"{}"'.format(lHexIp)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def validateMacAddress(value):
    if value is None:
        return

    m = re.match('([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', value)
    if m is None:
        raise BadParameter('Malformed mac address : %s' % value)

    lHexMac = ''.join([ '%02x' % int(c,16) for c in value.split(':')])
    return 'X"{}"'.format(lHexMac)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def printRegTable(aRegs, aHeader=True, aSort=True):
    echo ( formatRegTable(aRegs, aHeader, aSort) )
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def formatRegTable(aRegs, aHeader=True, aSort=True):
    lRegTable = Texttable(max_width=0)
    lRegTable.set_deco(Texttable.VLINES | Texttable.BORDER | Texttable.HEADER)
    lRegTable.set_chars(['-', '|', '+', '-'])
    if aHeader:
        lRegTable.header( ['name', 'value'] )

    lRegs = sorted(aRegs) if aSort else aRegs
    for k in lRegs:
        lRegTable.add_row( [str(k), hex(aRegs[k])] )
        
    return lRegTable.draw()
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def printDictTable(aDict, aHeader=True, aSort=True, aFmtr=None):
    echo ( formatDictTable(aDict, aHeader, aSort, aFmtr) )
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def formatDictTable(aDict, aHeader=True, aSort=True, aFmtr=str):
    lDictTable = Texttable(max_width=0)
    lDictTable.set_deco(Texttable.VLINES | Texttable.BORDER | Texttable.HEADER)
    lDictTable.set_chars(['-', '|', '+', '-'])
    if aHeader:
        lDictTable.header( ['name', 'value'] )

    for k in (sorted(aDict) if aSort else aDict):
        v = aDict[k]
        lDictTable.add_row( [str(k), aFmtr(v) if aFmtr else v])
        
    return lDictTable.draw()
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def getClickRootName():
    return get_current_context().find_root().info_name
# ------------------------------------------------------------------------------
