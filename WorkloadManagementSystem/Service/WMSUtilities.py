########################################################################
# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/WorkloadManagementSystem/Service/WMSUtilities.py,v 1.17 2009/04/23 07:32:53 rgracian Exp $
########################################################################

""" A set of utilities used in the WMS services
"""

__RCSID__ = "$Id: WMSUtilities.py,v 1.17 2009/04/23 07:32:53 rgracian Exp $"

from tempfile import mkdtemp
import shutil, os
from DIRAC.Core.Utilities.Subprocess import systemCall
from DIRAC.FrameworkSystem.Client.ProxyManagerClient       import gProxyManager

from DIRAC import S_OK, S_ERROR

# List of files to be inserted/retrieved into/from pilot Output Sandbox
# first will be defined as StdOut in JDL and the second as StdErr
outputSandboxFiles = [ 'StdOut', 'StdErr', 'std.out', 'std.err' ]

COMMAND_TIMEOUT = 60
###########################################################################
def getPilotOutput( proxy, grid, pilotRef ):
  """
   Get Output of a GRID job
  """
  tmp_dir = mkdtemp()
  if grid == 'LCG':
    cmd = [ 'edg-job-get-output' ]
  elif grid == 'gLite':
    cmd = [ 'glite-wms-job-output','--vo','lhcb' ]
  else:
    return S_ERROR( 'Unknnown GRID %s' % grid  )

  cmd.extend( ['--noint','--dir', tmp_dir, pilotRef] )

  ret = _gridCommand( proxy, cmd )
  if not ret['OK']:
    shutil.rmtree(tmp_dir)
    return ret

  status,output,error = ret['Value']
  if error.find('already retrieved') != -1:
    shutil.rmtree(tmp_dir)
    return S_ERROR('Pilot job output already retrieved')

  if error.find('Output not yet Ready') != -1 :
    shutil.rmtree(tmp_dir)
    return S_ERROR(error)

  if output.find('not yet ready') != -1 :
    shutil.rmtree(tmp_dir)
    return S_ERROR(output)

  if status:
    shutil.rmtree(tmp_dir)
    return S_ERROR(error)

  # Get the list of files

  if grid == 'LCG':
    # LCG always creates an unique sub-directory
    tmp_dir = os.path.join(tmp_dir,os.listdir(tmp_dir)[0])

  result = S_OK()
  result['FileList'] = outputSandboxFiles

  for filename in [ os.path.join( tmp_dir, x ) for x in outputSandboxFiles ]:
    if os.path.exists(filename):
      file = file(filename,'r')
      f = file.read()
      file.close()
    else:
      f = ''
    # HACK: removed after the current scheme has been in production for at least 1 week
    if filename == 'std.out': filename = 'StdOut'
    if filename == 'std.err': filename = 'StdErr'
    result[filename] = f

  shutil.rmtree(tmp_dir)
  return result

###########################################################################
def getPilotLoggingInfo( proxy, grid, pilotRef ):
  """
   Get LoggingInfo of a GRID job
  """
  if grid == 'LCG':
    cmd = [ 'edg-job-get-logging-info', '-v', '2' ]
  elif grid == 'gLite':
    cmd = [ 'glite-wms-job-logging-info', '-v', '3' ]
  else:
    return S_ERROR( 'Unknnown GRID %s' % grid  )

  cmd.extend( ['--noint', pilotRef] )

  ret = _gridCommand( proxy, cmd )
  if not ret['OK']:
    return ret

  status,output,error = ret['Value']
  if status:
    return S_ERROR(error)

  return S_OK( output )

def _gridCommand( proxy, cmd):
  """
   Execute cmd tuple
  """
  gridEnv = dict(os.environ)

  ret = gProxyManager.dumpProxyToFile( proxy )
  if not ret['OK']:
    return ret
  gridEnv[ 'X509_USER_PROXY' ] = ret['Value']
  gridEnv[ 'LOGNAME' ]         = 'dirac'

  return systemCall( COMMAND_TIMEOUT, cmd, env = gridEnv )

