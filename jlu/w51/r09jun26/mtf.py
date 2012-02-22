import pdb
import pyfits
import numpy as np
import pylab as py
import math, asciidata
import shutil
from scipy import fftpack
from jlu.util import radialProfile
import find_apertures
import pickle
from pyraf import iraf as ir
from jlu.nirc2.mtf import mtf
from gcreduce import gcutil
from gcwork import objects


def run_mtf():
    """
    Run the MTF fitting code on the H, K', L' images to get an
    estimate of the 
    """
    # all the images are pulled from the data directory
    images = ['mag09jun26_w51a_wide_h',
              'mag09jun26_w51a_wide_kp',
              'mag09jun26_w51a_f1_lp',
              'mag09jun26_w51a_f2_lp',
              'mag09jun26_w51a_f3_lp',
              'mag09jun26_w51a_f4_lp']

    resolvedSources = [[[608.6, 747.4]],
                       [[609.6, 613.5]],
                       [[905.7, 903.6]],
                       None,
                       None,
                       None]


    xcenter = [None, 611, None, None, None, None]
    ycenter = [750, 614, None, None, None, None]

    for ii in range(len(images)):
        call_fit_mtf(images[ii], resolvedSources=resolvedSources[ii],
                     xcenter=xcenter[ii], ycenter=ycenter[ii])

def run_mtf_non_photo():
    """
    Run the MTF fitting code on the H, K', L' images to get an
    estimate of the 
    """
    # all the images are pulled from the data directory
    images = ['mag09jun10_w51a_f1_kp',
              'mag09jun10_w51a_f2_kp',
              'mag09jun10_w51a_f3_kp',
              'mag09jun26_w51a_f4_kp',
              'mag09jun26_w51a_f1_h',
              'mag09jun26_w51a_f2_h',
              'mag09jun26_w51a_f3_h',
              'mag09jun26_w51a_f4_h']

    resolvedSources = [[[870, 870]],
                       None,
                       None,
                       None,
                       [[876, 876]],
                       None,
                       None,
                       None]

    for ii in range(len(images)):
        if '09jun10' in images[ii]:
            dataDir = '/u/jlu/data/w51/09jun10/combo/'
        if '09jun26' in images[ii]:
            dataDir = '/u/jlu/data/w51/09jun26/combo/'
            
        call_fit_mtf(images[ii], resolvedSources=resolvedSources[ii],
                     dataDir=dataDir)

    
def print_mtf_results():
    # all the images are pulled from the data directory
    roots = ['mag09jun10_w51a_f1_kp',
             'mag09jun10_w51a_f2_kp',
             'mag09jun10_w51a_f3_kp',
             'mag09jun26_w51a_f4_kp',
             'mag09jun26_w51a_f1_h',
             'mag09jun26_w51a_f2_h',
             'mag09jun26_w51a_f3_h',
             'mag09jun26_w51a_f4_h',
             'mag09jun26_w51a_wide_h',
             'mag09jun26_w51a_wide_kp',
             'mag09jun26_w51a_f1_lp',
             'mag09jun26_w51a_f2_lp',
             'mag09jun26_w51a_f3_lp',
             'mag09jun26_w51a_f4_lp']
    
    _params = open('mtf_best_fit_params.dat', 'w')

    for rr in range(len(roots)):
        pickleFile = open(roots[rr] + '_mtf.pickle', 'r')
        obs = pickle.load(pickleFile)
        fit = pickle.load(pickleFile)

        # Print out the best fit parameters used to generate the MTF
        if (rr == 0):
            _params.write('%-25s  ' % '#ImageName')
            for key, value in fit.all_params.items():
                _params.write('%10s  ' % key)
            _params.write('\n')
            
        _params.write('%-25s  ' % roots[rr])
        for value in fit.all_params.values():
            if type(value) == str:
                _params.write('%10s  ' % value)
            else:
                _params.write('%10.3g  ' % value)
        _params.write('\n')

        # Make a plot of the observed vs. best-fit power spectrum.
        py.clf()
        py.semilogy(obs.nu, obs.pspec, 'r-', label='Observed', linewidth=2)
        py.semilogy(obs.nu, fit.pspec_fit, 'k-', label='Best Fit', linewidth=2)
        py.legend()
        py.xlabel('Spatial Frequency (1 = lambda/D)')
        py.ylabel('Power')
        py.title(roots[rr])
        py.savefig('mtf_' + roots[rr] + '_pspec.png')

    _params.close()

def apertureCorrections(root, plot=True, silent=False,
                        stfDir='/u/jlu/data/w51/09jun26/combo/',
                        mtfDir='/u/jlu/work/w51/photo_calib/09jun26/science_fields/mtf/',
                        outDir='./',
                        innerAper=None, outerAper=None):
    """
    innerAper - (default = None, use filter-dependent dictionary in function).
                Set to narrow camera pixels (even if image is wide camera).
    outerAper - (default = None, use filter-dependent dictionary in function).
                Set to narrow camera pixels (even if image is wide camera).
    """

    aperSTFbyFilter = {'h': 12, 'kp': 12, 'lp': 12}
    aperSTDbyFilter = {'h': 160, 'kp': 130, 'lp': 20}

    filter = root.split('_')[-1]

    if innerAper == None:
        apSTF = aperSTFbyFilter[filter]
    else:
        apSTF = innerAper

    if outerAper == None:
        apSTD = aperSTDbyFilter[filter]
    else:
        apSTD = outerAper

    camera = 'narrow'
    scale = 0.00995
    
    # Correct for wide camera
    if 'wide' in root:
        camera = 'wide'
        scale = 0.04
        apSTF /= 4
        apSTD /= 4

    # ##########
    # PSF from starfinder
    # ##########
    psf2d_stf = pyfits.getdata(stfDir + root + '_psf.fits')
    foo = radialProfile.azimuthalAverage(psf2d_stf)
    psf_stf_r = foo[0]
    psf_stf = foo[1]
    psf_stf_err = foo[2] / np.sqrt(foo[3]) # error on the mean
    psf_stf_npix = foo[3]
        
    # ##########
    # PSF from MTF code
    # ##########
    pickleFile = open(mtfDir + root + '_mtf.pickle', 'r')
    obs = pickle.load(pickleFile)
    fit = pickle.load(pickleFile)
    psf2d_mtf = fit.psf2d
    foo = radialProfile.azimuthalAverage(psf2d_mtf)
    psf_mtf_r = foo[0]
    psf_mtf = foo[1]
    psf_mtf_err = foo[2] / np.sqrt(foo[3])  # error on the mean
    psf_mtf_npix = foo[3]
    #psf_mtf = fit.psf1d
    #psf_mtf_r = np.arange(len(psf_mtf), dtype=float)

    # Normalize MTF PSF, so that it peaks at 1.0
    #renorm = psf_mtf[0]
    #psf_mtf /= renorm
    #psf_mtf_err /= renorm

    # Convert radii to arcsec
    psf_mtf_r *= scale  # in arcsec
    psf_stf_r *= scale  # in arcsec

    # Normalize the Starfinder PSF to the first 3 radial bins
    # covering the core. r is still in pixels
    core_radius = 2 * 0.05
    min_r = max([psf_stf_r[0], psf_mtf_r[0]]) # Smallest radius to both
    idx_stf = np.where((psf_stf_r >= min_r) & (psf_stf_r < core_radius))[0]
    idx_mtf = np.where((psf_mtf_r >= min_r) & (psf_mtf_r < core_radius))[0]
    core_flux_stf = psf_stf[idx_stf].sum()
    core_flux_mtf = psf_mtf[idx_mtf].sum()

    norm_factor = (core_flux_mtf / core_flux_stf)#.mean()
    
    psf_stf *= norm_factor
    psf_stf_err *= norm_factor
    
    # ##########
    # Calc Aperutre Corrections
    # ##########
    npix_inner = psf_mtf_npix[0:apSTF]
    npix_outer = psf_mtf_npix[apSTF:apSTD]

    # 1. Get the Starfinder flux out to the specified STF aperture
    flux_stf_inner = (psf_stf[0:apSTF] * npix_inner).sum()

    # 2. Get the Starfinder flux out to the edge of the PSF
    flux_stf_all = (psf_stf * psf_stf_npix).sum()

    # 3. Get the MTF flux out to the specified STF aperture
    flux_mtf_inner = (psf_mtf[0:apSTF] * npix_inner).sum()
    flux_mtf_inner_err = ((psf_mtf_err[0:apSTF] * npix_inner)**2).sum()
    flux_mtf_inner_err = math.sqrt(flux_mtf_inner_err)
    
    # 4. Get the MTF flux out to the specified standard star aperture
    flux_mtf_outer = (psf_mtf[apSTF:apSTD] * npix_outer).sum()
    flux_mtf_outer_err = ((psf_mtf_err[apSTF:apSTD] * npix_outer)**2).sum()
    flux_mtf_outer_err = math.sqrt(flux_mtf_outer_err)

    # 5. Calculate the aperture correction (in magnitudes) to 
    #    go from Starfinder total fluxes, to standard star apertures.
    stf2stfIn_flux = flux_stf_inner / flux_stf_all
    stf2stan_flux = (1.0 + (flux_mtf_outer / flux_mtf_inner)) * stf2stfIn_flux
    stf2stan_mags = -2.5 * math.log10(stf2stan_flux)

    # 5. Calculate errors
    err1 = (stf2stfIn_flux * flux_mtf_outer_err / flux_mtf_inner)**2
    err2 = (stf2stfIn_flux * flux_mtf_outer * flux_mtf_inner_err / flux_mtf_inner**2)**2

    stf2stan_flux_err = np.sqrt(err1 + err2)
    stf2stan_mags_err = 2.5 * math.log10(math.e) 
    stf2stan_mags_err *= stf2stan_flux_err / stf2stan_flux

    
    if silent == False:
        # ##########
        # Printing
        # ##########
        print ''
        print '*** APERTURE CORRECTIONS FOR %s ***' % root
        #print 'err1 = ', err1, ' err2 = ', err2
        #print 'stf2stfIn_flux = ', stf2stfIn_flux


        print 'Science Aperture Size  = %d %s pixels (%.3f arcsec)' % \
            (apSTF, camera, apSTF * scale)
        print 'Standard Aperture Size = %d %s pixels (%.3f arcsec)' % \
            (apSTD, camera, apSTD * scale)
        print 'PSFs normalized at radius = %.2f arcsec,  factor = %.3f' % \
            (core_radius, norm_factor)
        
        print ''
        print 'STF Flux within STF Aperture: %f' % (flux_stf_inner)
        print 'MTF Flux within STF Aperture: %f' % (flux_mtf_inner)
        print 'MTF Flux within STD Aperture: %f' % \
            (flux_mtf_inner + flux_mtf_outer)
        print ''
        print 'Aperture Correction to go from Starfinder Magnitudes'
        print 'to Standard Apparent Magnitudes:'
        print '    Flux Ratio = %.3f +/- %.3f' % \
            (stf2stan_flux, stf2stan_flux_err)
        print '    Mag Differ = %.3f +/- %.3f' % \
            (stf2stan_mags, stf2stan_mags_err)
        print '    Stan Flux = STF Flux * %.3f' % (stf2stan_flux)
        print '    Stan Mags = STF Mags + %.3f + ZP' % (stf2stan_mags)
        
    if plot == True:
        # ##########
        # Plotting
        # ##########
        # Plot PSFs
        py.figure(1)
        py.clf()
        py.semilogy(psf_stf_r, psf_stf, 'b-', label='STF', linewidth=2)
        py.plot(psf_mtf_r, psf_mtf, 'k-', label='MTF', linewidth=2)

        psf_lo = psf_stf-psf_stf_err
        psf_hi = psf_stf+psf_stf_err
        idx = np.where(psf_lo > 0)[0]
        py.fill_between(psf_stf_r[idx], psf_lo[idx], y2=psf_hi[idx],
                        color='blue', alpha=0.5)
        # Show where the normalization occurs.
        py.plot(psf_mtf_r[idx_mtf], psf_mtf[idx_mtf], 'r-', 
                    linewidth=2, 
                    label='_nolabel_')
        py.legend()
        py.xlabel('Radius (arcsec)')
        py.ylabel('Point Spread Function Intensity')
        py.xlim(0, 1.0)
        py.title(root)
        py.savefig(outDir + 'mtf_' + root + '_psfs.png')

        
        # ----------
        # Encircled Energy:
        # Renormalize the MTF PSF such that integrating it gives
        # us the encircled energy.
        # ----------
        # EE from MTF code
        ee_mtf2 = fit.encircled_energy
        ee_mtf2_r = np.arange(0, len(ee_mtf2)) * scale

        # EE from integrating the MTF PSF
        ee_mtf = (psf_mtf * psf_mtf_npix).cumsum()
        ee_mtf_r = psf_mtf_r

        # Find the radii at which they overlap
        min_r = ee_mtf_r[0]
        max_r = min([ee_mtf_r[-1], ee_mtf2_r[-1]])
        idx_mtf2 = np.where((ee_mtf2_r >= min_r) & 
                            (ee_mtf2_r <= max_r))[0]
        idx_mtf = np.where((ee_mtf_r >= min_r) & 
                           (ee_mtf_r <= max_r))[0]
        
        # Calculate a normalization factor assuming the MTF EE is truth
        norm_factor_mtf = (ee_mtf2[idx_mtf2] / ee_mtf[idx_mtf]).mean()

        ee_mtf *= norm_factor_mtf

        # EE from integrating the STF PSF (renormalized also)
        ee_stf = (psf_stf * psf_stf_npix).cumsum() * norm_factor_mtf
        ee_stf_r = psf_stf_r

        py.figure(2)
        py.clf()
        py.plot(ee_stf_r, ee_stf, 'b-', label='STF', linewidth=2)
        py.plot(ee_mtf_r, ee_mtf, 'k-', label='MTF', linewidth=2)
        py.plot(ee_mtf2_r, ee_mtf2, 'k--', label='MTF2', linewidth=2)
        py.legend()
        py.xlabel('Radius (arcsec)')
        py.ylabel('Encircled Energy')
        py.xlim(0, 1.0)
        py.title(root)
        py.savefig(outDir + 'mtf_' + root + '_ee.png')

    return (stf2stan_flux, stf2stan_flux_err, stf2stan_mags, stf2stan_mags_err)
    

def allApertureCorrections():
    """
    Take the PSF from each science exposure and compare it to the
    1D PSF predicted from the MTF fitting code. The two PSFs are normalized
    to each other using the diffraction limited core only. Then
    the deviation between the core and the PSF tells us at what radius we
    should trust the Starfinder photometry.
    """
    roots = ['mag09jun10_w51a_f1_kp',
             'mag09jun10_w51a_f2_kp',
             'mag09jun10_w51a_f3_kp',
             'mag09jun26_w51a_f4_kp',
             'mag09jun26_w51a_f1_h',
             'mag09jun26_w51a_f2_h',
             'mag09jun26_w51a_f3_h',
             'mag09jun26_w51a_f4_h',
             'mag09jun26_w51a_wide_h',
             'mag09jun26_w51a_wide_kp',
             'mag09jun26_w51a_f1_lp',
             'mag09jun26_w51a_f2_lp',
             'mag09jun26_w51a_f3_lp',
             'mag09jun26_w51a_f4_lp']


    dataDir = '/u/jlu/data/w51/09jun26/combo/'
    for rr in range(len(roots)):
        if '09jun26' in roots[rr]:
            dataDir = '/u/jlu/data/w51/09jun26/combo/'
        else:
            dataDir = '/u/jlu/data/w51/09jun10/combo/'

        apertureCorrections(roots[rr], stfDir=dataDir, plot=True, silent=False)
    
def call_fit_mtf(imageRoot, dataDir='/u/jlu/data/w51/09jun26/combo/',
                 starsSuffix='_0.8_stf.lis', resolvedSources=None,
                 maskSize=150, xcenter=None, ycenter=None,
                 clip=0.02, weights=None, outDir='./'):
    """
    weights - {None, 'std', 0.1} where the last can be any scale factor.
             None = no weighting, or same as constant weights.
             'std' = use 1 / standard deviation of averaged 1D power spectrum.
             <frac> = use 1 / (any scale factor * 'std')
    """
    ##############################
    # H-band wide image
    ##############################
    imageFile = dataDir + imageRoot + '.fits'
    img, hdr = pyfits.getdata(imageFile, header=True)
    wavelength = hdr['CENWAVE'] * 1e-6
    focallength = mtf.Fvalues[hdr['CAMNAME'].strip()]
    pupil = hdr['PMSNAME']

    # Mask resolved sources
    if resolvedSources != None:
        print 'MTF: Masking %d resolved sources' % len(resolvedSources)
        img = mask_image(imageFile, resolvedSources, maskSize=maskSize)
    gcutil.rmall([outDir + imageRoot + '_masked.fits'])
    pyfits.writeto(outDir + imageRoot + '_masked.fits', img)

    print 'MTF: Set initial guesses for parameters'
    #definitions of starting parameters [from fitmtf_keck.pro]
    #
    #    wave=1.65d-6          # wavelength in meters
    #    F=557.0               # effective focal length of Keck AO (narrow)
    #    D=10.99               # primary's diameter in meters
    #    pupil=0.266           # central obscuration
    #    pupil='largehex'      # NIRC2 pupil-stop
    #    Apix=27d-6            # width of detector's pixel in meters
    #    L0=20.                # outer scale of turbulence in meters
    #    sigma=.56             # Infl Func width on primary in meters
    #    w=1.3                 # Influence Function height
    #    Delta=0               # wavefront measurement error
    #    Cmult=10.             # multiplicative constant
    #    N=1d-2                # additive noise floor constant
    #    r0=0.5                # wavelength specific fried parameter in meters
    startp = {'wave': wavelength,
              'D': 10.99, 'F': focallength, 'Apix': 27e-6, 'pupil': pupil, 
              'r0': 0.5, 'L0': 30.0, 'cmult': 1.0, 'N': 1e-5, 'w': 1.3, 
              'delta': 0.0, 'sigma': 0.56,}

    # Load up the starfinder results for this image
    print 'MTF: Read in preliminary starlist.'
    stfLis = dataDir + 'starfinder/' + imageRoot + starsSuffix
    table = asciidata.open(stfLis)
    name = table[0].tonumpy()
    mag = table[1].tonumpy()
    x = table[3].tonumpy()
    y = table[4].tonumpy()
    flux = 10**((mag[0] - mag)/2.5)

    # Create sources array (delta functions * flux) for the stars.
    print 'MTF: Creating 2D source array'
    sources = np.zeros(img.shape, dtype=float)
    sources[np.array(y, dtype=int), np.array(x, dtype=int)] = flux

    # If this is a wide camera image, trim down to the central 512x512
    # in order to limit the impact of anisoplanatism.
    if hdr['CAMNAME'].strip() == 'wide':
        # Make image square
        new_size = (np.array(img.shape) / 2.0).min()
        xlo = xcenter - (new_size/2)
        xhi = xcenter + (new_size/2)
        ylo = ycenter - (new_size/2)
        yhi = ycenter + (new_size/2)

        img = img[ylo:yhi, xlo:xhi]
        
        sources = sources[ylo:yhi, xlo:xhi]

        py.figure(2)
        py.clf()
        py.imshow(np.log10(img))
        py.draw()

        py.figure(1)

    print 'MTF: Calling getmtf'
    foo = mtf.get_mtf(img, startp, sources=sources)

    nu = foo[0]
    power = foo[1]
    error = foo[2]
    pspec_sources = foo[3]

    weightMsg = 'Weighting by 1 / STD of azimuthal average power spectrum'

    # Defuault, assume weight = 'std' and just use the 
    # standard deviation of azimuthal average of the power spectrum.
    if weights == None:
        weightMsg = 'Unweighted'
        error = np.ones(len(error))
    if (type(weights) == float) and (weights <= 1) and (weights > 0):
        weightMsg = 'Weighting by 1 / power * scaleFactor of %.3f' % weights
        error = power * weights
    print weightMsg
    
    # Fit the power spectrum
    print 'MTF: Fitting the power spectrum (round 1)'
    fit = mtf.fitmtf_keck(nu, power, error, pspec_sources, 
                          startParams=startp, relStep=0.2, clip=clip)
    print 'MTF: Fitting the power spectrum (round 2)'
    fit = mtf.fitmtf_keck(nu, power, error, pspec_sources, 
                          startParams=fit.params, relStep=0.02, clip=clip)

    pspec_fit = mtf.mtffunc_keck(fit.params, nu=nu, sources=pspec_sources)
    mtfOut = mtf.mtffunc_keck(fit.params, nu=nu)

    print 'Calculating PSF'    # PSF
    psf2d, psf1d = mtf.mtf2psf(fit.params, 2.0)

    print 'Calculating EE '    # Encircled Energy
    pix = np.arange(100, dtype=float)
    ee = mtf.mtf2ee(fit.params, pix)

    print 'Calculating Strehl' # Strehl
    sr = mtf.strehl(fit.params)

    # Make some output objects
    p_obs = objects.DataHolder()
    p_obs.nu = nu
    p_obs.pspec = power
    p_obs.pspec_error = error
    p_obs.pspec_sources = pspec_sources

    p_fit = objects.DataHolder()
    p_fit.all_params = fit.params
    p_fit.all_errors = fit.perror
    p_fit.fit_params = fit.fit_params
    p_fit.fit_covar = fit.fit_covar
    p_fit.fit_stat = fit.fit_stat
    p_fit.pspec_fit = pspec_fit
    p_fit.mtf_system = mtfOut
    p_fit.mtf_perfect = fit.tperf
    p_fit.psf1d = psf1d
    p_fit.psf2d = psf2d
    p_fit.strehl = sr
    p_fit.encircled_energy = ee

    # Save output to a pickle file
    outfile = open(outDir + imageRoot + '_mtf.pickle', 'w')
    pickle.dump(p_obs, outfile)
    pickle.dump(p_fit, outfile)
    outfile.close()





##############################
# This is the old stuff (IDL and 
# playing/developing the python version).
##############################

def mtf_play(imageRoot, dataDir='/u/jlu/data/w51/09jun26/combo/',
             starsSuffix='_0.8_stf.lis', resolvedSources=None,
             maskSize=150):
    import pidly

    idl = pidly.IDL()

    ##############################
    # H-band wide image
    ##############################
    imageFile = dataDir + imageRoot + '.fits'
    img, hdr = pyfits.getdata(imageFile, header=True)
    wavelength = hdr['CENWAVE'] * 1e-6
    
    # Mask resolved sources
    if resolvedSources != None:
        print 'MTF: Masking %d resolved sources' % len(resolvedSources)
        img = mask_image(imageFile, resolvedSources, maskSize=maskSize)
    gcutil.rmall([imageRoot + '_masked.fits'])
    pyfits.writeto(imageRoot + '_masked.fits', img)

    # Load up the image
    print 'MTF: Load the science image.'
    idl('im = readfits("' + imageRoot + '_masked.fits")')

    print 'MTF: Set initial guesses for parameters'
    #definitions of starting parameters [from fitmtf_keck.pro]
    #
    #    lambda=1.65d-6        # wavelength in meters
    #    F=557.0               # effective focal length of Keck AO (narrow)
    #    D=10.99               # primary's diameter in meters
    #    pupil=0.266           # central obscuration
    #    pupil='largehex'      # NIRC2 pupil-stop
    #    Apix=27d-6            # width of detector's pixel in meters
    #    L0=20.                # outer scale of turbulence in meters
    #    sigma=.56             # Infl Func width on primary in meters
    #    w=1.3                 # Influence Function height
    #    Delta=0               # wavefront measurement error
    #    Cmult=10.             # multiplicative constant
    #    N=1d-2                # additive noise floor constant
    #    r0=0.5                # wavelength specific fried parameter in meters
    idl('startp = {lambda:' + str(wavelength) + ', ' +
        'D:10.99, F:139.9, APIX:27e-6, ' +
        'pupil:"largehex", L0:30.0, SIGMA:0.56, ' +
        'W:1.3, Delta:0.0, Cmult:1.0, N:1e-5, R0:0.5}')
    
    # Load up the starfinder results for this image
    print 'MTF: Read in preliminary starlist.'
    stfLis = dataDir + 'starfinder/' + imageRoot + starsSuffix
    idl('readcol, "' + stfLis + '", name, mag, time, x, y, ' + 
        'snr, corr, frames, fwhm, format="(A,F,F,F,F,F,F,F,F)"')
    idl('flux = 10^((mag[0] - mag)/2.5)')

    # Create sources array (delta functions * flux) for the stars.
    print 'MTF: Creating 2D source array'
    idl('sources = im')
    idl('sources[*] = 0.')
    idl('sources[x, y] = flux')

    mtfData = imageRoot + '_mtfdata.save'
    mtfFit = imageRoot + '_mtffit.save'

    print 'MTF: Calling getmtf'
    idl('getmtf, im, startp, nu, power, error, spdist, deltas=sources')
    idl('save, nu, power, error, spdist, filename="'+mtfData+'"')

    # Fit the power spectrum
    print 'MTF: Fitting the power spectrum (round 1)'
    idl('print, startp')
    idl('fitmtf_keck, "'+mtfData+'", params, perror, ' +
        'start=startp, relstep=0.2')
#     print 'MTF: Fitting the power spectrum (round 2)'
#     idl('fitmtf_keck, "'+mtfData+'", params, perror, ' +
#         'start=params, relstep=0.02')
#     idl('save, params, perror, filename="'+mtfFit+'"')
    

def mtf_plot_results(imageRoot, dataDir='/u/jlu/data/w51/09jun26/combo/',
                     starsSuffix='_0.8_stf.lis'):
    img, hdr = pyfits.getdata(dataDir + imageRoot + '.fits', header=True)

    import pidly
    idl = pidly.IDL()

    print 'MTF: Restoring IDL variables'
    mtfData = imageRoot + '_mtfdata.save'
    mtfFit = imageRoot + '_mtffit.save'
    idl('restore, "' + mtfData + '"')
    idl('restore, "' + mtfFit + '"')
    
    ##########
    # Plot the 1D and 2D power spectrum of the source distribution
    ##########
    stfLis = dataDir + 'starfinder/' + imageRoot + starsSuffix
    _lis = asciidata.open(stfLis)
    mag = _lis[1].tonumpy()
    x = _lis[3].tonumpy()
    y = _lis[4].tonumpy()
    flux = 10**((mag[0] - mag)/2.5)

    sources = np.zeros(img.shape, dtype=float)
    xpix = np.array(np.round(x), dtype=int)
    ypix = np.array(np.round(y), dtype=int)
    sources[xpix, ypix] = flux

    F = fftpack.fftshift( fftpack.fft2(sources) )
    psd2D = np.abs(F)**2 
    psd1D = radialProfile.azimuthalAverage(psd2D)
    
#     py.figure(1)
#     py.clf()
#     py.imshow(np.log10(psd2D))

#     py.figure(2)
#     py.clf()
#     py.semilogy(psd1D)
#     py.xlabel('Spatial Frequency')
#     py.ylabel('Power Spectrum')
    
#     py.figure(3)
#     py.clf()
#     py.semilogy(idl.nu, idl.spdist)
#     py.xlabel('Spatial Frequency')
#     py.ylabel('Power Spectrum')
#     py.show()

    ##########
    # Plot up the best-fit power spectrum
    ##########
    print params
    idl('pspec_fit = mtffunc_keck(nu, params, spdist=spdist)')
    idl('mtf = mtffunc_keck(nu, params)')
    
    nu = idl.nu
    power = idl.power
    pspec_fit = idl.pspec_fit
    mtf = idl.mtf
    resid = power - pspec_fit

    print nu.shape
    print pspec_fit.shape

    py.clf()
#     py.semilogy(nu, power)
    py.semilogy(nu, pspec_fit)
#     py.semilogy(nu, mtf)
#     py.semilogy(nu, np.abs(resid))
    py.xlabel('Spatial Frequency')
    py.ylabel('Power Spectrum')
    py.legend(('Data', 'Best Fit', 'MTF', 'Residuals'))
    py.show()

# #     print 'Calculating PSF'    # PSF
# #     idl('mtf2psf, params, 2.0, psf2d, psf1d')

# #     print 'Calculating EE '    # Encircled Energy
# #     idl('pix = findgen(100)')
# #     idl('mtf2ee, params, pix, ee')

# #     print 'Calculating Strehl' # Strehl
# #     idl('sr = strehl(params)')


# #     py.clf()
# #     py.semilogy(idl.nu, idl.power)
# #     py.xlabel('Spatial Frequency')
# #     py.ylabel('Power')
# #     py.show()

# #     # 1D PSF
# #     py.figure(1)
# #     py.clf()
# #     py.plot(idl.psf1d)

# #     # 2D PSF
# #     py.figure(2)
# #     py.clf()
# #     py.imshow(np.log10(idl.psf2d))

# #     # Encircled Energy
# #     py.figure(3)
# #     py.clf()
# #     py.plot(idl.pix, idl.ee)

# #     # Print out Strehl
# #     print 'Resulting MTF Strehl = %.2f' % idl.sr

# #     py.show()
    

def fft_play(imageRoot, dataDir='/u/jlu/data/w51/09jun26/combo/',
             starsSuffix='_0.8_stf.lis'):
    ##############################
    # H-band wide image
    ##############################
    
    img, hdr = pyfits.getdata(dataDir + imageRoot + '.fits', header=True)

    F = fftpack.fftshift( fftpack.fft2(img) )
    psd2D_im = np.abs(F)**2
    psd1D_im = radialProfile.azimuthalAverage(psd2D_im)

    py.figure(1)
    py.clf()
    py.imshow(np.log10(img))

    py.figure(2)
    py.clf()
    py.imshow(np.log10(psd2D_im))

    py.figure(3)
    py.clf()
    py.semilogy(psd1D_im)
            
    py.show()

    ##########
    # H-band wide *_sig.fits image
    ##########
    img, hdr = pyfits.getdata(dataDir + imageRoot + '_sig.fits', header=True)

    F = fftpack.fftshift( fftpack.fft2(img) )
    psd2D_sig = np.abs(F)**2
    psd1D_sig = radialProfile.azimuthalAverage(psd2D_sig)

    py.figure(2)
    py.clf()
    py.semilogy(psd1D_sig)
    py.show()


    ##########
    # Source List
    ##########
    stfLis = dataDir + 'starfinder/' + imageRoot + starsSuffix
    _lis = asciidata.open(stfLis)
    mag = _lis[1].tonumpy()
    x = _lis[3].tonumpy()
    y = _lis[4].tonumpy()
    flux = 10**((mag[0] - mag)/2.5)

    sources = np.zeros(img.shape, dtype=float)
    xpix = np.array(np.round(x), dtype=int)
    ypix = np.array(np.round(y), dtype=int)
    sources[xpix, ypix] = flux

    F = fftpack.fftshift( fftpack.fft2( sources ))
    psd2D_src = np.abs(F)**2
    psd1D_src = radialProfile.azimuthalAverage(psd2D_src)

    py.figure(1)
    py.clf()
    py.imshow(np.log10(psd2D_src))

    py.figure(2)
    py.clf()
    py.semilogy(psd1D_src)
            
    py.show()

    # Plot all 1D PSDs
    py.figure(1)
    py.clf()
    py.semilogy(psd1D_im - psd1D_sig)
    py.semilogy(psd1D_sig)
    py.semilogy(psd1D_src)
    py.show()



def mask_image(imageFile, resolvedSources, maskSize=150):
    img = pyfits.getdata(imageFile)

    # Calculate the sky level for this image.
    text_output = ir.imstatistics(imageFile, fields='mean', nclip=10, 
                                  lsigma=10, usigma=2, format=0, Stdout=1)
    backLevel = float(text_output[0])
    
    backImage = img * 0.0 + backLevel
        
    imgNoBack = img - backImage

    # Make a mask image.
    for rr in range(len(resolvedSources)):
        coords = resolvedSources[rr]

        if type(maskSize) == int:
            msize = maskSize
        elif len(maskSize) > 1:
            msize = maskSize[rr]

        mask1D = np.hanning(msize)
        mask = -1.0 * np.outer(mask1D, mask1D) + 1.0
        
        # Find the image borders
        m_xlo = coords[1] - msize/2
        m_xhi = m_xlo + msize
        m_ylo = coords[0] - msize/2
        m_yhi = m_ylo + msize
        i_xhi = imgNoBack.shape[0]
        i_yhi = imgNoBack.shape[1]
        
        if m_xlo < 0:
            mask = mask[abs(m_xlo):,:]
            m_xlo = 0
        if m_ylo < 0:
            mask = mask[:,abs(m_ylo):]
            m_ylo = 0
        if m_xhi > i_xhi:
            mask = mask[:i_xhi - m_xhi,:]
            m_xhi = i_xhi
        if m_yhi > i_yhi:
            mask = mask[:,:i_yhi - m_yhi]
            m_yhi = i_yhi

        imgNoBack[m_xlo:m_xhi, m_ylo:m_yhi] *= mask

        img = imgNoBack + backImage

    return img
