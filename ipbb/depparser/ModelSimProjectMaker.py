from __future__ import print_function
import time, os

from Pathmaker import Pathmaker
from os.path import join, split, exists, splitext, abspath
from ..tools.common import SmartOpen

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class ModelSimProjectMaker( object ):
  #--------------------------------------------------------------
  def __init__( self , aPathmaker ):
    self.Pathmaker = aPathmaker
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def write( self , aTarget, aScriptVariables , aComponentPaths , aCommandList , aLibs, aMaps ):

    #----------------------------------------------------------
    # FIXME: Tempourary assignments
    write = aTarget
    lWorkingDir = abspath( join( os.getcwd() , 'top' ) )
    #----------------------------------------------------------

    #----------------------------------------------------------

    write('# Autogenerated project build script')
    write( time.strftime('# %c') )
    write( )

    for setup in aCommandList['setup']:
      write( 'source {0}'.format( setup.FilePath ) )
      
    write('vlib work')
    
    for lib in aLibs:
      write('vlib {0}'.format( lib ))
    
    for ma in aMaps:
      write('vmap {0} {1}'.format( ma[0], ma[1] ))
      write('vcom -work {0} -refresh -force_refresh'.format( ma[0] ))
    
    #----------------------------------------------------------
    for src in reversed( aCommandList['src'] ):

      #----------------------------------------------------------
      if src.Include:
    
        lPath , lBasename = split( src.FilePath )
        lName, lExt = splitext( lBasename  )
        lMap = src.Map

        #----------------------------------------------------------
        if lExt == '.xco':
          file = abspath( join( lPath , lName + '.vhd' ) )
        elif lExt == '.xci':
          # Hack required. The Vivado generated hdl files sometimes have 'sim' in their path, sometimes don't
          file = None
          lIpPath = abspath( join( lWorkingDir , 'top.srcs' , 'sources_1' , 'ip') )
          
          #----------------------------------------------------------
          for lDir in ['','sim']:
            for lExt in ['vhd','v']:
              lPathToIp = join(lIpPath,lName,lDir,lName+'.'+lExt)
              if not exists(join(lPathToIp)): continue

              file = lPathToIp
              break
            # File found, stop here
            if file is not None: break
          #----------------------------------------------------------

          if file is None:
            raise IOError('No simulation source found for core '+lBasename)
          #----------------------------------------------------------
        else:
          file = src.FilePath
        #----------------------------------------------------------
          
        #----------------------------------------------------------
        if splitext(file)[1] == '.vhd':
          if src.Vhdl2008:
            cmd = 'vcom -2008'
          else:
            cmd = 'vcom'
        elif splitext(file)[1] == '.v':
          cmd = 'vlog'
        
        elif lMap != None:
          continue

        else:
          print( '# IGNORING unknown source file type in Modelsim build: {0}'.format(src.FilePath) )
          continue
        #----------------------------------------------------------
       
        if src.Lib:
          cmd = '{0} -work {1}'.format(cmd, src.Lib)
        #----------------------------------------------------------

      write( '{0} {1}'.format( cmd , file ) )
      #----------------------------------------------------------

#--------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------