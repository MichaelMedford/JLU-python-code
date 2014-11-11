import os, errno, shutil
import pyfits
import pdb
import glob
import numpy as np
import math
from astropy.io import fits

def rmall(files):
    """Remove list of files without confirmation."""
    for file in files:
        if os.access(file, os.F_OK): os.remove(file)


def mkdir(dir):
    """Make directory if it doesn't already exist."""
    try: 
        os.makedirs(dir)
    except OSError, exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def getcwd():
    """
    IRAF doesn't like long file names. This reduces them.
    """
    
    curdir = os.getcwd()
    
    newdir1 = curdir.replace('/net/uni/Groups/ghez/ghezgroup', '/u/ghezgroup')
    newdir2 = newdir1.replace('/net/uni/Groups/ghez/jlu', '/u/jlu/work')
    newdir3 = newdir2.replace('/net/dione/data0/ghez', '/u/ghezgroup')
    newdir4 = newdir3.replace('/scr2/jlu/data', '/u/jlu/data')
    newdir4 +=  '/'

    return newdir4

def trimdir(olddir):
    """
    IRAF doesn't like long file names. This reduces them.
    """
    newdir1 = olddir.replace('/net/uni/Groups/ghez/ghezgroup', '/u/ghezgroup')
    newdir2 = newdir1.replace('/net/uni/Groups/ghez/jlu', '/u/jlu/work')
    newdir3 = newdir2.replace('/net/dione/data0/ghez', '/u/ghezgroup')
    newdir4 = newdir3.replace('/scr2/jlu/data', '/u/jlu/data')
    return newdir4

def cp_change_prefix(arg1,arg2):
    """
    Takes files beginning with arg1 and replaces them with arg2
    Must be in the directory where files live
    """

    # Find files in this directory beginning with arg1
    files = os.listdir(".")
    # Ignore files beginning with '.'
    files=[filename for filename in files if filename[0] != '.']

    ln = len(arg1)

    for ff in range(len(files)):
        pre = files[ff][0:ln]
        if pre == arg1:
            suf = files[ff][len(arg1):]
            newFile = arg2 + suf
            shutil.copy(files[ff], newFile)


def cp_change_suffix(arg1,arg2):
    """
    Takes files ending with arg1 and replaces them with arg2
    Must be in the directory where files live
    """

    # Find files in this directory ending with arg1
    files = os.listdir(".")
    # Ignore files beginning with '.'
    files=[filename for filename in files if filename[0] != '.']

    ln = len(arg1)

    for ff in range(len(files)):
        suf = files[ff][len(files[ff])-len(arg1):]
        if suf == arg1:
            pre = files[ff][0:len(files[ff])-len(arg1)]
            newFile = pre + arg2 
            shutil.copy(files[ff], newFile)



def read_log(filename):
    f = open(filename)
    frames =[] 
    obj = []
    filt1 = []
    ra = []
    dec = []
    date = []
    exptime = []
    coadds = []
    mjd = []
    for lines in f:
        dum = lines.split()
        frames.append(dum[0])
        obj.append(dum[1])
        filt1.append(dum[2])
        ra.append(dum[3])
        dec.append(dum[4])
        date.append(dum[5])
        exptime.append(dum[6])
        coadds.append(int(dum[7]))
        mjd.append(float(dum[8]))
        
    return np.array(frames), np.array(obj), np.array(filt1), np.array(ra), np.array(dec), np.array(date), np.array(exptime), np.array(coadds), np.array(mjd)
    
def mk_log(directory, output='gsaoi_log.txt'):
    """
    Read in all the fits files in the specified directory and print
    out a log containing the useful header information.

    directory - the directory to search for *.fits files
    output - the output file to print the information to
    """
    files = glob.glob(directory + '/*.fits')

    _out = open(directory + '/' +  output, 'w')

    for ff in files:
        hdr = fits.getheader(ff)

        line = ''

        dir, filename = os.path.split(ff)
        fileroot, fileext = os.path.splitext(filename)
        line += '{0:16} '.format(fileroot)
        
        line += '{0:15s} '.format(hdr['OBJECT'].replace(" ",""))
        line += '{0:15s} '.format(hdr['FILTER1'])

        ra = hdr['RA']
        raHour = math.floor(ra) * 24.0 / 360.0
        raMin = (ra % 1) * 60
        raSec = (raMin % 1) * 60
        line += '{0:2d}:{1:0>2d}:{2:0>5.2f} '.format(int(raHour), int(raMin), raSec)

        dec = hdr['DEC']
        decDeg = math.floor(dec)
        decMin = (dec % 1) * 60
        decSec = (dec % 1) * 60
        line += '{0:3d}:{1:0>2d}:{2:0>5.2f}  '.format(int(decDeg), int(decMin), decSec)

        line += '{0} '.format(hdr['DATE-OBS'])
        line += '{0:6.2f} '.format(hdr['EXPTIME'])
        line += '{0:3d} '.format(hdr['COADDS'])
        line += '{0:8.2f}'.format(hdr['MJD-OBS'])

        line += '\n'

        _out.write(line)

    _out.close()
    return directory + '/' +  output
