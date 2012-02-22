import pylab as py
import numpy as np
import atpy
import asciidata
import math
import pdb
import pyfits
import pycurl
import coords
import os
from gcwork import objects
from pyraf import iraf

##################################################
#
# Upper Sco
#
##################################################
def upper_sco():
    rootDir = '/u/jlu/doc/proposals/irtf/2012A/'

    # Read in a reference table for converting between
    # spectral types and effective temperatures.
    ref = atpy.Table(rootDir + 'Teff_SpT_table.txt', type='ascii')

    sp_type = np.array([ii[0] for ii in ref.col1])
    sp_class = np.array([float(ii[1:4]) for ii in ref.col1])
    sp_teff = ref.col2
    
    # Read in the upper sco table
    us = atpy.Table(rootDir + 'upper_sco_sample_simbad.txt', type='ascii')

    us_sp_type = np.array([ii[0] for ii in us.spectype])
    us_sp_class = np.zeros(len(us_sp_type), dtype=int)
    us_sp_teff = np.zeros(len(us_sp_type), dtype=int)

    for ii in range(len(us_sp_class)):
        if (us_sp_type[ii] == "~"):
            us_sp_class[ii] = -1
        else:
            if ((len(us.spectype[ii]) < 2) or
              (us.spectype[ii][1].isdigit() == False)):
                us_sp_class[ii] = 5  # Arbitrarily assigned
            else:
                us_sp_class[ii] = us.spectype[ii][1]

            # Assign effective temperature
            idx = np.where(us_sp_type[ii] == sp_type)[0]
            tdx = np.abs(us_sp_class[ii] - sp_class[idx]).argmin()
            us_sp_teff[ii] = sp_teff[idx[tdx]]
            
    # Trim out the ones that don't have spectral types and K-band
    # magnitudes for plotting purposes.
    idx = np.where((us_sp_type != "~") & (us.K != "~") & (us.J != "~"))[0]
    print 'Keeping %d of %d with spectral types and K mags.' % \
        (len(idx), len(us_sp_type))

    us.add_column('sp_type', us_sp_type)
    us.add_column('sp_class', us_sp_class)
    us.add_column('sp_teff', us_sp_teff)

    us = us.rows([idx])

    J = np.array(us.J[0], dtype=float)
    H = np.array(us.H[0], dtype=float)
    K = np.array(us.K[0], dtype=float)
    JKcolor = J - K


    # Get the unique spectral classes and count how many of each
    # we have in the sample.
    sp_type_uniq = np.array(['O', 'B', 'A', 'F', 'G', 'K', 'M', 'L', 'T'])
    sp_type_count = np.zeros(len(sp_type_uniq), dtype=int)
    sp_type_idx = []

    sp_type_J = np.zeros(len(sp_type_uniq), dtype=float)
    sp_type_JK = np.zeros(len(sp_type_uniq), dtype=float)

    for ii in range(len(sp_type_uniq)):
        idx = np.where(us.sp_type[0] == sp_type_uniq[ii])[0]
        sp_type_count[ii] = len(idx)

        sp_type_idx.append(idx)

        # Calc the mean J and J-K color for each spectral type
        if len(idx) > 2:
            sp_type_J[ii] = J[idx].mean()
            sp_type_JK[ii] = JKcolor[idx].mean()

        print '%s  %3d  J = %4.1f  J-K = %4.1f' % \
            (sp_type_uniq[ii], sp_type_count[ii],
             sp_type_J[ii], sp_type_JK[ii])


    # Plot up the distribution of spectral types
    xloc = np.arange(len(sp_type_uniq)) + 1
    py.clf()
    py.bar(xloc, sp_type_count, width=0.5)
    py.xticks(xloc+0.25, sp_type_uniq)
    py.xlim(0.5, xloc.max()+0.5)
    py.xlabel('Spectral Type')
    py.ylabel('Upper Sco Sample')
    py.savefig(rootDir + 'USco_spec_type_hist.png')

    # Plot Teff vs. J-band mag
    py.clf()
    py.semilogx(us.sp_teff[0], J, 'k.')
    rng = py.axis()
    py.axis([rng[1], rng[0], rng[3], rng[2]])
    py.xlabel('Teff (K, log scale)')
    py.ylabel('J Magnitude')
    py.xlim(40000, 1000)
    py.savefig(rootDir + 'USco_HR.png')

    py.clf()
    py.plot(JKcolor, J, 'kx')

    idx = np.where(sp_type_J != 0)[0]
    py.plot(sp_type_JK[idx], sp_type_J[idx], 'bs')
    for ii in idx:
        py.text(sp_type_JK[ii]+0.05, sp_type_J[ii]-0.5, sp_type_uniq[ii], color='blue')
    rng = py.axis()
    py.axis([rng[0], rng[1], rng[3], rng[2]])
    py.xlabel('J - K (mag)')
    py.ylabel('J (mag)')
    py.xlim(-0.25, 1.75)
    py.savefig(rootDir + 'USco_CMD.png')

    idx = np.where(J < 11)[0]
    print '%d stars with J<11 and Teff = [%3d - %4d] K' % \
        (len(idx), us.sp_teff[0][idx].min(), us.sp_teff[0][idx].max())
    
    
    return us

    
def spex_snr(tint, mag, band):
    snr0 = 10.0   # sigma
    tint0 = 60.0  # min
    mag0 = {'J': 14.6, 'H': 14.1, 'K': 13.7}

    snr = snr0 * 10**(-(mag - mag0[band])/2.5) * math.sqrt(tint / tint0 )
    return snr
    
##################################################
#
# CEMP-no origin
#
##################################################
    

frebel_elements = ['Li', 'C', 'N', 'O', 'Na', 'Mg', 'Al', 'Si', 'Ca', 'Sc', 
                   'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Zn', 'Ga',
		   'Ge', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Ru', 'Rh', 'Pd',
		   'Ag', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
		   'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Os',
		   'Ir', 'Pt', 'Au', 'Pb', 'Th', 'U']
dwarf_spheroidals = ['Boo', 'Car', 'Com', 'Dra', 'Fnx', 'Her', 'Leo', 'S10',
                     'S11', 'S12', 'S14', 'S15', 'Sci', 'Sex', 'Sta', 'Uma',
                     'UMi']

dir = '/u/jlu/doc/proposals/keck/caltech/11B/'

def cemp_no_properties():
    d = load_frebel_table()

    # Lets identify some sub-samples. Criteria from Beers 2008.
    emp = np.where((d.CFe < 0.9) & (d.ra != -999) & (d.V > 0) &
		   (d.FeH != -999) & (d.CFe != -999) & (d.BaFe != -999))[0]
    empr = np.where((d.CFe < 0.9) & (d.ra != -999) & (d.V > 0) &
		   (d.FeH != -999) & (d.CFe != -999) & (d.BaFe != -999) &
		   (d.BaEu < 0))[0]
    cemp = np.where(d.CFe >= 0.9)[0]
    cempr = np.where((d.CFe >= 0.9) & (d.EuFe > 1))[0]
    cemps = np.where((d.CFe >= 0.9) & (d.BaFe > 1) & 
                     (d.EuFe > -999) & (d.BaEu > 0.5))[0]
    cempno = np.where((d.CFe >= 0.9) & (d.BaFe > -999) & (d.BaFe < 0))[0]

    # Plot up the histogram of Iron abundances:
    bins_FeH = np.arange(-7, 1, 0.5)
    py.clf()
    py.hist(d.FeH, histtype='step', bins=bins_FeH, 
            label='%d stars' % len(d.name))
    py.hist(d.FeH[cemp], histtype='step', bins=bins_FeH, 
            label='%d CEMP' % len(cemp))
    py.hist(d.FeH[cemps], histtype='step', bins=bins_FeH, 
            label='%d CEMP-s' % len(cemps))
    py.hist(d.FeH[cempno], histtype='step', bins=bins_FeH, 
            label='%d CEMP-no' % len(cempno))
    py.xlabel('[Fe/H]')
    py.ylabel('Number')
    py.legend(loc='upper left')
    py.ylim(0, 100)
    py.savefig(dir + 'hist_FeH.png')


    # Fix the ones with no V-band magnitudes
    bad_s = np.where(d.V[cemps] < 0)[0]
    bad_no = np.where(d.V[cempno] < 0)[0]

    # Bad CEMP-s stars
    print ''
    print '## Bad CEMP-s'
    for ii in bad_s:
        print '%20s  %10.5f  %10.5f  %5.2f' % \
            (d.name[cemps[ii]], d.ra[cemps[ii]], 
             d.dec[cemps[ii]], d.V[cemps[ii]])

    print '## Bad CEMP-no'
    for ii in bad_no:
        print '%20s  %10.5f  %10.5f  %5.2f' % \
            (d.name[cempno[ii]], d.ra[cempno[ii]], 
             d.dec[cempno[ii]], d.V[cempno[ii]])

    # Get rid of the stars without info.
    cemps = np.delete(cemps, bad_s)
    cempno = np.delete(cempno, bad_no)

    # Fix the RA and Dec for CEMP-s and CEMP-no stars
    d.ra[cemps], d.dec[cemps] = getCoordsFromSimbad(d.simbad[cemps])
    d.ra[cempno], d.dec[cempno] = getCoordsFromSimbad(d.simbad[cempno])

    py.clf()
    py.plot(d.V[cemps], d.FeH[cemps], 'rs', label='CEMP-s')
    py.plot(d.V[cempno], d.FeH[cempno], 'bo', label='CEMP-no')
    py.legend(loc='upper left', numpoints=1)
    py.xlabel('V magnitude')
    py.ylabel('[Fe/H]')
    py.savefig('v_vs_feh_cemp_s_no.png')

    # Now lets figure out what is observable this semester.
    py.clf()
    py.plot(d.ra[cemps], d.dec[cemps], 'rs', label='CEMP-s')
    py.plot(d.ra[cempno], d.dec[cempno], 'bo', label='CEMP-no')
    py.xlabel('R.A. (degrees)')
    py.ylabel('Dec. (degrees)')
    py.legend(loc='upper right', numpoints=1)

    lim_RA_mar01 = [ 90, 237]
    lim_RA_may01 = [156, 284]
    lim_RA_jul01 = [223, 342]
    
    py.plot(lim_RA_mar01, [10, 10], 'm-', linewidth=3)
    py.plot(lim_RA_may01, [20, 20], 'k-', linewidth=3, color='cyan')
    py.plot(lim_RA_jul01, [30, 30], 'g-', linewidth=3)
    py.text(95, 12, 'Mar 01, 2012', color='magenta')
    py.text(160, 22, 'May 01, 2012', color='cyan')
    py.text(235, 32, 'Jul 01, 2011', color='green')
    py.xlim(0, 360)
    py.ylim(-30, 70)
    py.savefig('ra_dec_cemp_s_no.png')


    # RA vs. V-band
    py.clf()
    py.plot(d.ra[cemps], d.V[cemps], 'rs', label='CEMP-s')
    py.plot(d.ra[cempno], d.V[cempno], 'bo', label='CEMP-no')
    py.xlabel('R.A. (degrees)')
    py.ylabel('V Magnitude')
    py.gca().set_ylim(py.gca().get_ylim()[::-1])
    py.legend(loc='upper right', numpoints=1)

    py.plot(lim_RA_mar01, [12, 12], 'm-', linewidth=3)
    py.plot(lim_RA_may01, [11, 11], 'k-', linewidth=3, color='cyan')
    py.plot(lim_RA_jul01, [10, 10], 'g-', linewidth=3)
    py.text(95, 11.9, 'Mar 01, 2012', color='magenta')
    py.text(160, 10.9, 'May 01, 2012', color='cyan')
    py.text(235, 9.9, 'Jul 01, 2011', color='green')
    py.xlim(0, 360)
    py.ylim(17, 6)
    py.savefig('ra_v_cemp_s_no.png')

    print('')
    print 'After removing stars without info:'

    hdrfmt = '{:16s} {:^15s}  {:^15s}  {:^5s}  {:^5s}  {:^5s}  {:^5s}'
    starfmt = '{:<16s} {:15s}  {:15s}  {:5.2f}  {:5.2f}  {:5.2f}  {:5.2f}'

    # Print out all the emp-r stars
    print('')
    print('  {:d} EMP-r stars (non-Carbon enhanced)'.format(len(empr)))
    print(hdrfmt.format('Name', 'RA', 'Dec', 'Vmag',
			 'Fe/H', 'C/Fe', 'Ba/Fe'))
    for ii in empr:
        hmsdms = coords.Position((d.ra[ii], d.dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0].replace(':', ' ')
        dec_hex = hmsdms[1].replace(':', ' ')

        print(starfmt.format(d.name[ii], ra_hex, dec_hex, d.V[ii], 
			      d.FeH[ii], d.CFe[ii], d.BaFe[ii]))

    print('')
    print('  {:d} CEMP-s stars'.format(len(cemps)))
    print(hdrfmt.format('Name', 'RA', 'Dec', 'Vmag',
			 'Fe/H', 'C/Fe', 'Ba/Fe'))
    for ii in cemps:
        hmsdms = coords.Position((d.ra[ii], d.dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0].replace(':', ' ')
        dec_hex = hmsdms[1].replace(':', ' ')

        print(starfmt.format(d.name[ii], ra_hex, dec_hex, d.V[ii], 
			      d.FeH[ii], d.CFe[ii], d.BaFe[ii]))

    # Print out all the cemp-no stars
    print('')
    print('  {:d} CEMP-no stars'.format(len(cempno)))
    print(hdrfmt.format('Name', 'RA', 'Dec', 'Vmag',
			 'Fe/H', 'C/Fe', 'Ba/Fe'))
    for ii in cempno:
	print ii, d.ra[ii], d.dec[ii]
        hmsdms = coords.Position((d.ra[ii], d.dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0].replace(':', ' ')
        dec_hex = hmsdms[1].replace(':', ' ')

        print(starfmt.format(d.name[ii], ra_hex, dec_hex, d.V[ii], 
			      d.FeH[ii], d.CFe[ii], d.BaFe[ii]))



def load_frebel_table(verbose=False):
    d = objects.DataHolder()

    # Load fits table.
    data = pyfits.getdata(dir + 'frebel2010_fixed.fits')

    name = data.field('NAME')
    simbad = data.field('SIMBAD')
    ra = data.field('RA')
    dec = data.field('DEC')
    B = data.field('B')
    V = data.field('V')
    R = data.field('R')
    I = data.field('I')
    FeH = data.field('FEH')     # Iron abundance
    abundances = data.field('XFE') # All [X/Fe] abundances, carbon is idx=1
    upperlim = data.field('UPPERLIM')
    rv = data.field('RV')
    ref = data.field('ABUNDREF')

    refYear = np.zeros(len(ref), dtype=int)
    for rr in range(len(ref)):
        tmp = ref[rr][3:5]
        
        if tmp.startswith('0'):
            refYear[rr] = float('20%s' % tmp)
        else:
            refYear[rr] = float('19%s' % tmp)


    # Report how many stars don't have info:
    idx = np.where(ra < 0)[0]
    if verbose:
        print 'Found %d out of %d stars without information\n' % \
            (len(idx), len(name))

    idx_C = frebel_elements.index('C')
    idx_Ba = frebel_elements.index('Ba')
    idx_Eu = frebel_elements.index('Eu')
    
    # Pull out some elements of interest
    CFe = abundances[:, idx_C]
    BaFe = abundances[:, idx_Ba]
    EuFe = abundances[:, idx_Eu]
    BaEu = BaFe - EuFe

    # First we need to deal with duplicates
    if verbose:
        print '## Duplicates'
    duplicates = np.array([], dtype=int)
    for ii in range(len(name)):
        if ii in duplicates:
            # Already addressed this duplicate star, skip it
            continue

        idx = np.where(name == name[ii])[0]
        
        if len(idx) > 1:
            if verbose:
                print '%20s  %10.5f  %10.5f  %5.2f  %7.2f  %7.2f  %7.2f  %7.2f' % \
                    (name[ii], ra[ii], dec[ii], V[ii], FeH[ii], CFe[ii], 
                     BaFe[ii], EuFe[ii])

            # The easy case is where there is only one measurement
            # for a given element. Then we just take the one.
            good = np.where(FeH[idx] != 0)[0]
            if len(good) == 1:
                FeH[idx[0]] = FeH[idx][good[0]]
            if len(good) > 1:
                # otherwise take the most recent one
                recent = refYear[idx][good].argmax()
                FeH[idx[0]] = FeH[idx][good][recent]


            # The easy case is where there is only one measurement
            # for a given element. Then we just take the one.
            good = np.where(CFe[idx] > -999)[0]
            if len(good) == 1:
                CFe[idx[0]] = CFe[idx][good[0]]
            if len(good) > 1:
                # otherwise take the most recent one
                recent = refYear[idx][good].argmax()
                CFe[idx[0]] = CFe[idx][good][recent]
            if len(good) == 0:
                # No carbon measurements, get rid of star all together.
                if verbose:
                    print 'No C measurements for %s'  % name[ii]
                duplicates = np.append(duplicates, idx)

            # The easy case is where there is only one measurement
            # for a given element. Then we just take the one.
            good = np.where(BaFe[idx] > -999)[0]
            if len(good) == 1:
                BaFe[idx[0]] = BaFe[idx][good[0]]
            if len(good) > 1:
                # otherwise take the most recent one
                recent = refYear[idx][good].argmax()
                BaFe[idx[0]] = BaFe[idx][good][recent]

            # The easy case is where there is only one measurement
            # for a given element. Then we just take the one.
            good = np.where(EuFe[idx] > -999)[0]
            if len(good) == 1:
                EuFe[idx[0]] = EuFe[idx][good[0]]
            if len(good) > 1:
                # otherwise take the most recent one
                recent = refYear[idx][good].argmax()
                EuFe[idx[0]] = EuFe[idx][good][recent]

            if verbose:
                print '%20s  %10.5f  %10.5f  %5.2f  %7.2f  %7.2f  %7.2f  %7.2f' % \
                    (name[ii], ra[ii], dec[ii], V[ii], FeH[ii], CFe[ii], 
                     BaFe[ii], EuFe[ii])

            # Delete the other ones
            duplicates = np.append(duplicates, idx[1:])

    # Now delete the duplicates from the tables.
    d.name = np.delete(name, duplicates)
    d.simbad = np.delete(simbad, duplicates)
    d.ra = np.array(np.delete(ra, duplicates), dtype=float)
    d.dec = np.array(np.delete(dec, duplicates), dtype=float)
    d.B = np.array(np.delete(B, duplicates), dtype=float)
    d.V = np.array(np.delete(V, duplicates), dtype=float)
    d.R = np.array(np.delete(R, duplicates), dtype=float)
    d.I = np.array(np.delete(I, duplicates), dtype=float)
    d.FeH = np.array(np.delete(FeH, duplicates), dtype=float)
    d.abundances = np.array(np.delete(abundances, duplicates), dtype=float)
    d.rv = np.array(np.delete(rv, duplicates), dtype=float)
    d.ref = np.delete(ref, duplicates)
    d.refYear = np.delete(refYear, duplicates)
    d.CFe = np.array(np.delete(CFe, duplicates), dtype=float)
    d.BaFe = np.array(np.delete(BaFe, duplicates), dtype=float)
    d.EuFe = np.array(np.delete(EuFe, duplicates), dtype=float)
    d.BaEu = np.array(np.delete(BaEu, duplicates), dtype=float)

    if verbose:
        print '## Removed %d duplicates, %d stars left' % \
            (len(duplicates), len(name))


    return d

def load_masseron_table():
    data = pyfits.getdata('masseron2010.fits')
    d = objects.DataHolder()

    d.name = data.field('Name')
    d.type = data.field('Type')
    d.ra = data.field('_RA')
    d.dec = data.field('_DE')
    d.simbadName = data.field('SimbadName')
    d.FeH = data.field('[Fe/H]')
    d.CFe = data.field('[C/Fe]')
    d.BaFe = data.field('[Ba/Fe]')
    d.EuFe = data.field('[Eu/Fe]')
    d.BaEu = d.BaFe - d.EuFe

    d.V = getVbandFromSimbad(d.simbadName)
    
    return d

def getVbandFromSimbad(starNames):
    """
    Pull the star name (strip off any "*_" prefixes) and submit
    a query to simbad to find the radial velocity. If there is no
    entry, return 0.
    """
    # Write the simbad query
    queryFile = 'simbad_query.txt'
    _query = open(queryFile, 'w')
    _query.write('output console=off\n')
    _query.write('output script=off\n')
    _query.write('output error=off\n')
    _query.write('set limit 1\n')
    _query.write('format object fmt1 "%IDLIST(1), %FLUXLIST(V,R)[%*(F),]"\n')
    _query.write('result full\n')
    
    for ii in range(len(starNames)):
        _query.write('query id %s\n' % starNames[ii])

    _query.close()

    # Connect to simbad and submit the query. Save to a buffer.
    replyFile = 'simbad_results.txt'
    _reply = open(replyFile, 'w')
    curl = pycurl.Curl()
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.URL, 'http://simbad.harvard.edu/simbad/sim-script')
    curl.setopt(pycurl.WRITEFUNCTION, _reply.write)

    curlform = [("scriptFile", (pycurl.FORM_FILE, queryFile))]
    curl.setopt(pycurl.HTTPPOST, curlform)

    curl.perform()
    _reply.close()

    # Search reply for flux info.
    _reply = open(replyFile)
    foo = _reply.readlines()

    # Find the start of the data
    dataLine = 0
    simbadError = False
    for ff in range(len(foo)):
        if foo[ff].startswith('::data'):
            dataLine = ff
            break
        if (foo[ff].startswith('::error')):
            simbadError = True
            break
        
    vmag = np.zeros(len(starNames), dtype=float)

    if not simbadError:
        for ff in range(len(starNames)):
            fields = foo[dataLine+2+ff].split(',')
            msg = ''

            if (len(fields) > 1):
                # Found a valid entry
                vmagTmp = fields[1]  # last entry string in km/s
                
                if vmagTmp == '~':
                    vmagTmp = fields[2]
                    msg = '(using R-mag)'
                if vmagTmp == '~':
                    vmag[ff] = -999.0
                    msg = '(no data found)'
                    break

                if vmagTmp[0] is '-':
                    vmag[ff] = -1.0 * float(vmagTmp[1:])
                else:
                    vmag[ff] = float(vmagTmp)

            print 'SIMBAD: Found %s with V = %5.1f mag %s' % \
                (starNames[ff], vmag[ff], msg)
    else:
        print 'SIMBAD: Error on query'

    return vmag

def getCoordsFromSimbad(starNames):
    """
    Pull the star name (strip off any "*_" prefixes) and submit
    a query to simbad to find the radial velocity. If there is no
    entry, return 0.
    """
    # Write the simbad query
    queryFile = 'simbad_query.txt'
    _query = open(queryFile, 'w')
    _query.write('output console=off\n')
    _query.write('output script=off\n')
    _query.write('output error=off\n')
    _query.write('set limit 1\n')
    _query.write('format object fmt1 "%IDLIST(1),%COO(d;A),%COO(d;D)"\n')
    _query.write('result full\n')
    
    for ii in range(len(starNames)):
        _query.write('query id %s\n' % starNames[ii])

    _query.close()

    # Connect to simbad and submit the query. Save to a buffer.
    replyFile = 'simbad_results.txt'
    _reply = open(replyFile, 'w')
    curl = pycurl.Curl()
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.URL, 'http://simbad.harvard.edu/simbad/sim-script')
    curl.setopt(pycurl.WRITEFUNCTION, _reply.write)

    curlform = [("scriptFile", (pycurl.FORM_FILE, queryFile))]
    curl.setopt(pycurl.HTTPPOST, curlform)

    curl.perform()
    _reply.close()

    # Search reply for flux info.
    _reply = open(replyFile)
    foo = _reply.readlines()

    # Find the start of the data
    dataLine = 0
    simbadError = False
    for ff in range(len(foo)):
        if foo[ff].startswith('::data'):
            dataLine = ff
            break
        if (foo[ff].startswith('::error')):
            simbadError = True
            break
        
    ra = np.zeros(len(starNames), dtype=float)
    dec = np.zeros(len(starNames), dtype=float)

    if not simbadError:
        for ff in range(len(starNames)):
            fields = foo[dataLine+2+ff].split(',')
            msg = ''

            if (len(fields) > 2):
                # Found a valid entry
                ra[ff] = float(fields[1])
                dec[ff] = float(fields[2])

            print 'SIMBAD: Found %s at RA = %10.5f, DEC = %10.5f' % \
                (starNames[ff], ra[ff], dec[ff])
    else:
        print 'SIMBAD: Error on query'

    return ra, dec


def cempno_table():
    names = ['CD-38_245', 'CS22942-019', 'HD6755', 'CS22958-042', 
             'BD+44_493', 'BS16545-089', 'HE1150-0428', 'BS16920-005', 
             'HE1300+0157', 'BS16929-005', 'HE1300-0641', 'CS22877-001', 
             'CS22880-074', 'CS29498-043', 'CS29502-092', 'CS22949-037', 
             'CS22957-027', 'HE2356-0410', 'HE1012-1540', 'HE1330-0354']

    d = load_frebel_table()

    idx = np.array([], dtype=int)
    for ii in range(len(names)):
        foo = np.where(d.name == names[ii])[0]

        idx = np.append(idx, foo)

    sdx = d.ra[idx].argsort()
    idx = idx[sdx]

    # Trim out what we need
    ra = d.ra[idx]
    dec = d.dec[idx]
    V = d.V[idx]
    B = d.B[idx]
    R = d.R[idx]
    FeH = d.FeH[idx]
    CFe = d.CFe[idx]
    BaFe = d.BaFe[idx]

    # Fix the RA and Dec for CEMP-s and CEMP-no stars
    ra, dec = getCoordsFromSimbad(d.simbad[idx])

    # Make a LaTeX table of the targets we want to observe
    _out = open('table_cemp_no.tex', 'w')
    _out.write('\\begin{deluxetable}{lrrrrrr}\n')
    _out.write('\\tablewidth{0pt}\n')
    _out.write('\\tablecaption{CEMP-no Stars}\n')
    _out.write('\\tablehead{\n')
    _out.write('  \\colhead{Name} &\n')
    _out.write('  \\colhead{R.A. (J2000)} &\n')
    _out.write('  \\colhead{Dec. (J2000)} &\n')
    _out.write('  \\colhead{V} &\n')
    _out.write('  \\colhead{[Fe/H]} &\n')
    _out.write('  \\colhead{[C/Fe]} &\n')
    _out.write('  \\colhead{[Ba/Fe]}\n')
    _out.write('}\n')
    _out.write('\\startdata\n')
    
    for ii in range(len(names)):
        hmsdms = coords.Position((ra[ii], dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0]
        dec_hex = hmsdms[1]

        _out.write('%25s  & %15s  & %15s & ' % (names[ii].replace('_', '\_'), 
                                                ra_hex, dec_hex))
        _out.write('%5.2f  & %5.2f  & %5.2f  & %5.2f \\\\ \n' %
                   (V[ii], FeH[ii], CFe[ii], BaFe[ii]))

    _out.write('\\enddata\n')
    _out.write('\\end{deluxetable}\n')
    _out.close()



    # Now lets loop through and plot when these targets are observable.
    py.clf()
    py.subplots_adjust(left=0.05, right=0.95, top=0.95)
    
    # Calculate the hour angle at which the object goes above airmass = 2.
    # Relevant equations are: 
    #   airmass = 1 / cos(z)
    #   hour angle = sidereal time - RA
    #   cos z = sin L sin Dec + cos L cos Dec cos HA
    # We will solve for HA.
    iraf.noao()
    obs = iraf.noao.observatory
    obs(command="set", obsid="keck")
    airmassLim = 2.0

    latRad = np.radians(obs.latitude)
    decRad = np.radians(dec)

    top = (1.0 / airmassLim) - np.sin(latRad) * np.sin(decRad)
    bot = np.cos(latRad) * np.cos(decRad)

    hangle = np.degrees( np.arccos(top / bot) )

    madeLegend = False
    for ii in range(len(names)):
        minLST = (ra[ii] - hangle[ii]) / 15.
        maxLST = (ra[ii] + hangle[ii]) / 15.

        hix = 360.0 / 15.0

        if (minLST >= 0) and (maxLST < hix):
            if madeLegend == True:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black')
            else:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black', label='CEMP-no stars')
                madeLegend = True

        if minLST < 0:
            py.plot([0, maxLST], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([minLST + hix, hix], [ii+1, ii+1], linewidth=5, color='black')

        if maxLST > hix:
            py.plot([minLST, hix], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([0, maxLST - hix], [ii+1, ii+1], linewidth=5, color='black')


    py.xlim(0, hix)

    # Get the LST ranges for March, May, July
    months = np.array([3, 5, 7])
    days   = np.array([1, 1, 1])
    years  = np.array([2012, 2012, 2012])
    colors = ['red', 'green', 'blue']
    labels = ['Mar 1, 2012 (HST)', 'May 1, 2012 (HST)', 'Jul 1, 2012 (HST)']

    rng = py.axis()
    for ii in range(len(months)):
        twi = get_twilight_lst(years[ii], months[ii], days[ii])

        minLST = twi[0] * 15.0
        maxLST = twi[1] * 15.0

        ypos = rng[3] + 2*(len(months) - ii)

        if minLST < 0:
            minLST += 360.0
        if maxLST > 360:
            maxLST -= 360.0

        x1 = np.array([minLST, maxLST]) / 15.0
        x2 = None
        y = np.array([ypos, ypos])

        if minLST > 0 and maxLST < 360 and minLST > maxLST:
            x1 = np.array([0, maxLST]) / 15.0
            x2 = np.array([minLST, 360]) / 15.0
            

        py.plot(x1, y, linewidth=10, color=colors[ii], label=labels[ii])

        if x2 != None:
            py.plot(x2, y, linewidth=10, color=colors[ii])


    py.ylim(0, rng[3] + 7*len(months))
    py.legend(loc='upper left')
#     py.xlim(0, 360)
    py.xlim(0, 24)
    py.xlabel('LST (hours)')
    py.gca().yaxis.set_visible(False)
    py.savefig('obs_ra_v_cemp_s_no.png')


def cempno_starlist():
    names = np.array(['CD-38_245', 'CS22942-019', 'HD6755', 'CS22958-042', 
		       'BD+44_493', 'BS16545-089', 'HE1150-0428', 'BS16920-005', 
		       'HE1300+0157', 'BS16929-005', 'HE1300-0641', 'CS22877-001', 
		       'CS22880-074', 'CS29498-043', 'CS29502-092', 'CS22949-037', 
		       'CS22957-027', 'HE2356-0410', 'HE1012-1540', 'HE1330-0354'])

    d = load_frebel_table()

    idx = np.array([], dtype=int)
    for ii in range(len(names)):
        foo = np.where(d.name == names[ii])[0]

        idx = np.append(idx, foo)

#    sdx = d.ra[idx].argsort()
#    idx = idx[sdx]

    # Trim out what we need
    ra = d.ra[idx]
    dec = d.dec[idx]
    V = d.V[idx]
    B = d.B[idx]
    R = d.R[idx]
    FeH = d.FeH[idx]
    CFe = d.CFe[idx]
    BaFe = d.BaFe[idx]
    simbad = d.simbad[idx]

    # Fix the RA and Dec for CEMP-s and CEMP-no stars
    ra, dec = getCoordsFromSimbad(d.simbad[idx])

    # Make a LaTeX table of the targets we want to observe
    _out = open('cemp_no_starlist.tel', 'w')
    _out2 = open('cemp_no_simbadnames.tel', 'w')

    for ii in range(len(names)):
        hmsdms = coords.Position((ra[ii], dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0].replace(':', ' ')
        dec_hex = hmsdms[1].replace(':', ' ')

	print ii, names[ii], simbad[ii]

        _out.write('%-16s %12s %12s 2000.0 vmag=%5.2f\n' % (names[ii], ra_hex, dec_hex, V[ii]))
	_out2.write('%s\n' % simbad[ii])

    _out.close()
    _out2.close()


    # Now lets loop through and plot when these targets are observable.
    py.clf()
    py.subplots_adjust(left=0.05, right=0.95, top=0.95)
    
    # Calculate the hour angle at which the object goes above airmass = 2.
    # Relevant equations are: 
    #   airmass = 1 / cos(z)
    #   hour angle = sidereal time - RA
    #   cos z = sin L sin Dec + cos L cos Dec cos HA
    # We will solve for HA.
    iraf.noao()
    obs = iraf.noao.observatory
    obs(command="set", obsid="keck")
    airmassLim = 2.0

    latRad = np.radians(obs.latitude)
    decRad = np.radians(dec)

    top = (1.0 / airmassLim) - np.sin(latRad) * np.sin(decRad)
    bot = np.cos(latRad) * np.cos(decRad)

    print 'TOP: ', top, 'BOT: ', bot
    hangle = np.degrees( np.arccos(top / bot) )

    madeLegend = False
    for ii in range(len(names)):
        minLST = (ra[ii] - hangle[ii]) / 15.
        maxLST = (ra[ii] + hangle[ii]) / 15.

        hix = 360.0 / 15.0

        if (minLST >= 0) and (maxLST < hix):
            if madeLegend == True:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black')
            else:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black', label='CEMP-no stars')
                madeLegend = True

        if minLST < 0:
            py.plot([0, maxLST], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([minLST + hix, hix], [ii+1, ii+1], linewidth=5, color='black')

        if maxLST > hix:
            py.plot([minLST, hix], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([0, maxLST - hix], [ii+1, ii+1], linewidth=5, color='black')


    py.xlim(0, hix)

    # Get the LST ranges for March, May, July
    months = np.array([3, 5, 7])
    days   = np.array([1, 1, 1])
    years  = np.array([2012, 2012, 2012])
    colors = ['red', 'green', 'blue']
    labels = ['Mar 1, 2012 (HST)', 'May 1, 2012 (HST)', 'Jul 1, 2012 (HST)']

    rng = py.axis()
    for ii in range(len(months)):
        twi = get_twilight_lst(years[ii], months[ii], days[ii])

        minLST = twi[0] * 15.0
        maxLST = twi[1] * 15.0

        ypos = rng[3] + 2*(len(months) - ii)

        if minLST < 0:
            minLST += 360.0
        if maxLST > 360:
            maxLST -= 360.0

        x1 = np.array([minLST, maxLST]) / 15.0
        x2 = None
        y = np.array([ypos, ypos])

        if minLST > 0 and maxLST < 360 and minLST > maxLST:
            x1 = np.array([0, maxLST]) / 15.0
            x2 = np.array([minLST, 360]) / 15.0
            

        py.plot(x1, y, linewidth=10, color=colors[ii], label=labels[ii])

        if x2 != None:
            py.plot(x2, y, linewidth=10, color=colors[ii])


    py.ylim(0, rng[3] + 7*len(months))
    py.legend(loc='upper left')
#     py.xlim(0, 360)
    py.xlim(0, 24)
    py.xlabel('LST (hours)')
    py.gca().yaxis.set_visible(False)
    py.savefig('obs_ra_v_cemp_s_no_new.png')


def cempno_control_starlist():
    names = np.array(['HE0132-2429', 'HE1347-1025', 'HE1356-0622', 'HE1424-0241', 'BS16467-062',
		       'G64-12', 'CS29518-051', 'CS29502-042', 'CS22953-003',
		       'CS22896-154', 'CS22183-031', 'CS29491-069', 'CS29497-004', 'CS31082-001',
		       'HE0430-4901', 'HE0432-0923', 'HE1127-1143', 'HE1219-0312', 'HE2224+0143',
		       'HE2327-5642'])

    d = load_frebel_table()

    idx = np.array([], dtype=int)
    for ii in range(len(names)):
        foo = np.where(d.name == names[ii])[0]

	if len(foo) == 0:
	    print 'No star %s' % names[ii]
        idx = np.append(idx, foo)
    sdx = d.ra[idx].argsort()
    idx = idx[sdx]

    # Trim out what we need
    ra = d.ra[idx]
    dec = d.dec[idx]
    V = d.V[idx]
    B = d.B[idx]
    R = d.R[idx]
    FeH = d.FeH[idx]
    CFe = d.CFe[idx]
    BaFe = d.BaFe[idx]
    simbad = d.simbad[idx]

    # Fix the RA and Dec for CEMP-s and CEMP-no stars
    ra, dec = getCoordsFromSimbad(d.simbad[idx])

    # Make a LaTeX table of the targets we want to observe
    _out = open('control_starlist.tel', 'w')
    _out2 = open('control_simbadnames.tel', 'w')

    for ii in range(len(names)):
        hmsdms = coords.Position((ra[ii], dec[ii])).hmsdms().split()
        ra_hex = hmsdms[0].replace(':', ' ')
        dec_hex = hmsdms[1].replace(':', ' ')

	print ii, names[ii], simbad[ii]

        _out.write('%-16s %12s %12s 2000.0 vmag=%5.2f\n' % (names[ii], ra_hex, dec_hex, V[ii]))
	_out2.write('%s\n' % simbad[ii])

    _out.close()
    _out2.close()


    # Now lets loop through and plot when these targets are observable.
    py.clf()
    py.subplots_adjust(left=0.05, right=0.95, top=0.95)
    
    # Calculate the hour angle at which the object goes above airmass = 2.
    # Relevant equations are: 
    #   airmass = 1 / cos(z)
    #   hour angle = sidereal time - RA
    #   cos z = sin L sin Dec + cos L cos Dec cos HA
    # We will solve for HA.
    iraf.noao()
    obs = iraf.noao.observatory
    obs(command="set", obsid="keck")
    airmassLim = 2.0

    latRad = np.radians(obs.latitude)
    decRad = np.radians(dec)

    top = (1.0 / airmassLim) - np.sin(latRad) * np.sin(decRad)
    bot = np.cos(latRad) * np.cos(decRad)
    
    hangle = np.degrees( np.arccos(top / bot) )

    madeLegend = False
    for ii in range(len(names)):
        minLST = (ra[ii] - hangle[ii]) / 15.
        maxLST = (ra[ii] + hangle[ii]) / 15.

        hix = 360.0 / 15.0

        if (minLST >= 0) and (maxLST < hix):
            if madeLegend == True:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black')
            else:
                py.plot([minLST, maxLST], [ii+1, ii+1], linewidth=5, 
                        color='black', label='CEMP-no stars')
                madeLegend = True

        if minLST < 0:
            py.plot([0, maxLST], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([minLST + hix, hix], [ii+1, ii+1], linewidth=5, color='black')

        if maxLST > hix:
            py.plot([minLST, hix], [ii+1, ii+1], linewidth=5, color='black')
            py.plot([0, maxLST - hix], [ii+1, ii+1], linewidth=5, color='black')


    py.xlim(0, hix)

    # Get the LST ranges for March, May, July
    months = np.array([3, 5, 7])
    days   = np.array([1, 1, 1])
    years  = np.array([2012, 2012, 2012])
    colors = ['red', 'green', 'blue']
    labels = ['Mar 1, 2012 (HST)', 'May 1, 2012 (HST)', 'Jul 1, 2012 (HST)']

    rng = py.axis()
    for ii in range(len(months)):
        twi = get_twilight_lst(years[ii], months[ii], days[ii])

        minLST = twi[0] * 15.0
        maxLST = twi[1] * 15.0

        ypos = rng[3] + 2*(len(months) - ii)

        if minLST < 0:
            minLST += 360.0
        if maxLST > 360:
            maxLST -= 360.0

        x1 = np.array([minLST, maxLST]) / 15.0
        x2 = None
        y = np.array([ypos, ypos])

        if minLST > 0 and maxLST < 360 and minLST > maxLST:
            x1 = np.array([0, maxLST]) / 15.0
            x2 = np.array([minLST, 360]) / 15.0
            

        py.plot(x1, y, linewidth=10, color=colors[ii], label=labels[ii])

        if x2 != None:
            py.plot(x2, y, linewidth=10, color=colors[ii])


    py.ylim(0, rng[3] + 7*len(months))
    py.legend(loc='upper left')
#     py.xlim(0, 360)
    py.xlim(0, 24)
    py.xlabel('LST (hours)')
    py.gca().yaxis.set_visible(False)
    py.savefig('obs_ra_v_control_new.png')


def get_twilight_lst(year, month, day):
    """
    Get the 12-degree evening and morning twilight
    times (in LST) for the specified date.
    """
    # Get sunset and sunrise times on the first day
    scinName = 'skycalc.input'
    scoutName = 'skycalc.output'

    scin = open(scinName, 'w')
    scin.write('m\n')
    scin.write('y %4d %2d %2d a' % (year, month, day))
    scin.write('Q\n')
    scin.close()

    # Spawn skycalc
    os.system('skycalc < %s > %s' % (scinName, scoutName))

    # Now read in skycalc data
    scout = open(scoutName, 'r')
    lines = scout.readlines()
    

    for line in lines:
        fields = line.split()

        if (len(fields) < 3):
            continue

        if (fields[0] == 'Sunset'):
            sunset = float(fields[5]) + float(fields[6]) / 60.0
            sunset -= 24.0
            sunrise = float(fields[9]) + float(fields[10]) / 60.0

        if (fields[0] == '12-degr'):
            twilite1 = float(fields[2]) + float(fields[3]) / 60.0
            twilite1 -= 24.0
            twilite2 = float(fields[6]) + float(fields[7]) / 60.0

            print twilite1, twilite2
        if (fields[0] == 'Evening'):
            twilite1LST = float(fields[9]) + float(fields[10]) / 60.0
        if (fields[0] == 'Morning'):
            twilite2LST = float(fields[9]) + float(fields[10]) / 60.0

        if ((fields[0] == 'The') and (fields[1] == 'sun')):
            darkTime = (twilite2 - twilite1) - 0.5 # 0.5=LGS checkout
            splittime = twilite1 + 0.5 + darkTime/2
            if (splittime > 24.0):
                splittime -= 24.0

    return np.array([twilite1LST, twilite2LST])
    

        


    

    
