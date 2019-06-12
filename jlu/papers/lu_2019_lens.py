import numpy as np
import pylab as plt
from astropy.table import Table, Column, vstack
from astropy.io import fits
#from flystar import starlists
from scipy.interpolate import UnivariateSpline
from scipy.optimize import curve_fit, least_squares
from matplotlib.pylab import cm
from matplotlib.colors import Normalize, LogNorm
import os
from scipy.ndimage import gaussian_filter as norm_kde
from microlens.jlu import model_fitter, multinest_utils, multinest_plot, munge_ob150211, model
import dynesty.utils as dyutil
from matplotlib.colors import LinearSegmentedColormap, colorConverter
import pdb

ep_ob150211 = ['15may05', '15jun07', '15jun28', '15jul23', '16may03',
               '16jul14', '16aug02', '17jun05', '17jun08', '17jul19', 
               '18may11', '18aug02', '18aug16']

ep_ob150029 = ['15jun07', '15jul23', '16may24', '16jul14', '17may21',
               '17jul14', '17jul19', '18aug21']
    
ep_ob140613 = ['15jun07', '15jun28', '16apr17', '16may24', '16aug02',
               '17jun05', '17jul14', '18may11', '18aug16']

    
epochs = {'ob140613': ep_ob140613, 'ob150029': ep_ob150029, 'ob150211': ep_ob150211}

paper_dir = '/u/jlu/doc/papers/2015_bh_lenses/'

astrom_data = {'ob140613': '',
               'ob150029': '/u/jlu/work/microlens/OB150029/a_2019_04_19/ob150029_astrom_p3_2019_04_19.fits',
               'ob150211': '/u/jlu/work/microlens/OB150211/a_2019_05_04/ob150211_astrom_p3_2019_05_04.fits'}

comp_stars = {'ob140613': [],
              'ob150029': ['S002_16_0.3', 'S003_16_0.9'],
              'ob150211': ['S001_11_1.3', 'S003_14_1.4']}

pspl_ast_phot = {'ob140613': '',
                 'ob150029': '',
                 'ob150211': '/u/jlu/work/microlens/OB150211/a_2019_05_04/model_fits/4_fit_phot_astrom_parallax/bb_'}

def make_obs_table():
    """
    Make a LaTeX table for all of the observations of the three targets from 2014/2015.
    """

    targets = list(epochs.keys())

    tables = {}

    # Build three different tables with all the columns we need.
    for ii in range(len(targets)):
        target = targets[ii]
        n_epochs = len(epochs[target])
        
        obj_name = np.repeat(target.upper(), n_epochs)
        obj_name[1:] = ''
        
        date = np.zeros(n_epochs, dtype='S10')
        tint = np.zeros(n_epochs, dtype=int)
        n_exp = np.zeros(n_epochs, dtype=int)
        strehl = np.zeros(n_epochs, dtype=float)
        fwhm = np.zeros(n_epochs, dtype=float)
        strehl_e = np.zeros(n_epochs, dtype=float)
        fwhm_e = np.zeros(n_epochs, dtype=float)
        n_star = np.zeros(n_epochs, dtype=int)
        m_base = np.zeros(n_epochs, dtype=float)
        ast_err = np.zeros(n_epochs, dtype=float)
        phot_err = np.zeros(n_epochs, dtype=float)

        # Loop through each epoch and grab information to populate our table.
        for ee in range(n_epochs):
            epoch = epochs[target][ee]
            img_file = '/g/lu/data/microlens/{0:s}/combo/mag{0:s}_{1:s}_kp.fits'.format(epoch, target)
            log_file = '/g/lu/data/microlens/{0:s}/combo/mag{0:s}_{1:s}_kp.log'.format(epoch, target)
            pos_file = '/g/lu/data/microlens/{0:s}/combo/starfinder/plotPosError_{1:s}_kp.txt'.format(epoch, target)

            # Fetch stuff from the image header.
            hdr = fits.getheader(img_file)
            date[ee] = hdr['DATE-OBS'].strip()
            tint[ee] = np.round(float(hdr['ITIME']) * float(hdr['COADDS']), 0)

            # From the log file, average Strehl and FWHM
            _log = Table.read(log_file, format='ascii')
            _log.rename_column('col2', 'fwhm')
            _log.rename_column('col3', 'strehl')
            strehl[ee] = _log['strehl'].mean()
            strehl_e[ee] = _log['strehl'].std()
            fwhm[ee] = _log['fwhm'].mean()
            fwhm_e[ee] = _log['fwhm'].std()
            n_exp[ee] = len(_log)

            # Read in the stats file from the analysis of the AIROPA starlist.
            _pos = open(pos_file, 'r')
            lines = _pos.readlines()
            _pos.close()

            n_star[ee] = int(lines[0].split(':')[-1])
            ast_err[ee] = float(lines[1].split(':')[-1])
            phot_err[ee] = float(lines[2].split(':')[-1])
            m_base[ee] = float(lines[3].split('=')[-1])

        # Make our table
        c_obj_name = Column(data=obj_name, name='Object', format='{:13s}')
        c_date = Column(data=date, name='Date', format='{:10s}')
        c_tint = Column(data=tint, name='t$_{int}$', format='{:3.0f}', unit='s')
        c_nexp = Column(data=n_exp, name='N$_{exp}$', format='{:3d}')
        c_fwhm = Column(data=fwhm, name='FWHM', format='{:3.0f}', unit='mas')
        c_fwhm_err = Column(data=fwhm_e, name='FWHM$_{err}$', format='{:3.0f}', unit='mas')
        c_strehl = Column(data=strehl, name='Strehl', format='{:4.2f}')
        c_strehl_err = Column(data=strehl_e, name='Strehl$_{err}$', format='{:4.2f}')
        c_nstar = Column(data=n_star, name='N$_{star}$', format='{:4d}')
        c_mbase = Column(data=m_base, name='Kp$_{turn}$', format='{:4.1f}', unit='mag')
        c_asterr = Column(data=ast_err, name='$\sigma_{ast}$', format='{:5.2f}', unit='mas')
        c_photerr = Column(data=phot_err, name='$\sigma_{phot}$', format='{:5.2f}', unit='mag')
        
        tt = Table((c_obj_name, c_date, c_tint, c_nexp,
                    c_fwhm, c_fwhm_err, c_strehl, c_strehl_err,
                    c_nstar, c_mbase, c_asterr, c_photerr))

        tables[target] = tt

    # Smash all the tables together.
    final_table = vstack([tables['ob140613'], tables['ob150029'], tables['ob150211']])
    
    print(final_table)

    final_table.write(paper_dir + 'data_table.tex', format='aastex', overwrite=True)

    return

def perr_v_mag(mag, amp, index, mag_const, adderr):
    """
    Model for a positional error vs. magnitude curve. The
    functional form is:

    pos_err = adderr  +  amp * e^(index * (mag - mag_const))
    """
    perr = amp * np.exp(index * (mag - mag_const))
    perr += adderr

    return perr

def fit_perr_v_mag(params, mag, perr_obs):
    amp = params[0]
    index = params[1]
    mag_const = params[2]
    adderr = params[3]
    
    perr_mod = perr_v_mag(mag, amp, index, mag_const, adderr)

    resid = perr_obs - perr_mod

    return resid

def plot_pos_err():
    """
    Make one plot per target that shows the positional errors vs. magnitude for every epoch. 
    """
    targets = list(epochs.keys())
    
    plt.close('all')

    # NIRC2 palte scale (for 2015 Apr 13 and later)
    scale = 0.009971

    # Make a color scale that is the same for all of them.
    color_norm = Normalize(2015, 2019)
    cmap = cm.get_cmap('rainbow')

    # Loop through targets and make 1 plot each
    for tt in range(len(targets)):
    # for tt in range(1):
        target = targets[tt]
        n_epochs = len(epochs[target])

        plt.figure()

        # Calculate the pos error vs. mag curves for each epoch.
        # for ee in range(4):
        for ee in range(n_epochs):
            epoch = epochs[target][ee]
            
            pos_file = '/g/lu/data/microlens/{0:s}/combo/starfinder/mag{0:s}_{1:s}_kp_rms_named.lis'.format(epoch, target)

            lis = starlists.StarList.from_lis_file(pos_file)

            # Calc the 1D astrometric error by using the average over X and Y 
            perr = 0.5 * (lis['xe'] + lis['ye'])
            kmag = lis['m'] + np.random.rand(len(lis))*1e-5
            # col_idx = np.argmin(np.abs(color_times - lis['t'][0]))
            col = cmap(color_norm(lis['t'][0]))
            # print(ee, col_idx, col, color_times[col_idx], lis['t'][0])

            # REJECTED: Analytic Functional Forms and Fitting
            # Determine relation for perr vs. mag.
            # sdx = kmag.argsort()
            # spl = UnivariateSpline(kmag[sdx], perr[sdx], k=4)

            # # Determine relation for perr vs. mag from our exponential functional form
            # # (see Jia et al. 2019).
            # p0 = [1e-7, 0.7, 5, 1e-3]
            # popt, pcov = curve_fit(perr_v_mag, kmag, perr, p0=p0)
            # print(popt)

            # # Determine relation for perr vs. mag from our exponential functional form
            # # (see Jia et al. 2019). Now with outlier rejection.
            # res_lsq = least_squares(fit_perr_v_mag, p0, args=(kmag, perr))
            # res_lsq2 = least_squares(fit_perr_v_mag, p0, args=(kmag, perr), loss='cauchy', f_scale=0.01)

            # plt.plot(p_mag, spl(p_mag), label='spline')
            # plt.semilogy(p_mag, perr_v_mag(p_mag, *popt), label='curve_fit')
            # plt.semilogy(p_mag, perr_v_mag(p_mag, *res_lsq.x), label='lsq')

            
            # FIT a functional form similar to Jia et al. 2009 with outlier rejection.
            p0 = [1e-7, 0.7, 5, 1e-3]
            res_lsq2 = least_squares(fit_perr_v_mag, p0, args=(kmag, perr), loss='cauchy', f_scale=0.01)

            epoch_label = '20{0:2s} {1:s}{2:s} {3:2s}'.format(epoch[0:2], epoch[2].upper(), epoch[3:-2], epoch[-2:])

            # Make a magnitude array for the model curves.
            p_mag = np.arange(kmag.min(), kmag.max(), 0.05)

            # Plot the data
            # if ee == 0:
            #     plt.plot(kmag, perr * scale * 1e3, '.', label=epoch_label + ' (obs)', color=col, ms=2)
            
            plt.semilogy(p_mag, scale * 1e3 * perr_v_mag(p_mag, *res_lsq2.x), label=epoch_label, color=col)
            
        plt.legend(fontsize=12, loc='upper left', ncol=2)
        plt.xlabel('Kp mag')
        plt.ylabel('$\sigma_{ast}$ (mas)')
        plt.title(target.upper())
        plt.ylim(3e-2, 10)
        plt.savefig(paper_dir + 'pos_err_' + target + '.pdf')
            
    return

def plot_images():
    img_ob140613 = '/g/lu/data/microlens/18aug16/combo/mag18aug16_ob140613_kp.fits'
    img_ob150029 = '/g/lu/data/microlens/17jul19/combo/mag17jul19_ob150029_kp.fits'
    img_ob150211 = '/g/lu/data/microlens/17jun05/combo/mag17jun05_ob150211_kp.fits'

    images = {'ob140613': img_ob140613,
              'ob150029': img_ob150029,
              'ob150211': img_ob150211}

    def plot_image_for_source(target, vmin, vmax):
        combo_dir = os.path.dirname(images[target])
        img_base = os.path.basename(images[target])
        
        img = fits.getdata(images[target])

        psf_file = '/g/lu/data/microlens/source_list/' + target + '_psf.list'
        psf_tab = Table.read(psf_file, format='ascii')
        pdx = np.where(psf_tab['PSF?'] == 1)[0]
        psf_tab = psf_tab[pdx]

        lis_file = combo_dir + '/starfinder/' + img_base.replace('.fits', '_rms_named.lis')
        lis_tab = starlists.StarList.from_lis_file(lis_file)

        # Find the target and get its pixel coordinates in this image.
        tdx = np.where(lis_tab['name'] == target)[0]
        coo_targ = np.array([lis_tab['x'][tdx[0]], lis_tab['y'][tdx[0]]])
        coo_targ -= 1   # Shift to a 0-based array system

        # Define the axes
        scale = 0.00996
        x_axis = np.arange(img.shape[0], dtype=float)
        y_axis = np.arange(img.shape[1], dtype=float)
        x_axis = (x_axis - coo_targ[0]) * scale * -1.0
        y_axis = (y_axis - coo_targ[1]) * scale

        norm = LogNorm(vmin, vmax)

        plt.imshow(img, cmap='gist_heat_r', norm=norm, extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]])
        plt.plot([0], [0], 'c*', ms=15, mec='black', mfc='none', mew=2)
        plt.plot(psf_tab['Xarc'], psf_tab['Yarc'], 'go', ms=15, mec='green', mfc='none', mew=2)

        plt.axis('equal')
        plt.xlabel(r'$\Delta \alpha \;\cos\; \delta$ (")')
        plt.ylabel(r'$\Delta \delta$ (")')
        plt.title(target.upper())

        date_label = '20{0:2s} {2:3s} {2:2s}'.format(img_base[3:5], img_base[5:8].upper(), img_base[8:10])
        plt.gcf().text(0.2, 0.8, date_label, color='black')

        # plt.xlim(0.5, -0.5)
        # plt.ylim(-0.5, 0.5)

        return

    plt.figure(1)
    plt.clf()
    plot_image_for_source('ob140613', 10, 5e5)
    plt.savefig(paper_dir + 'img_ob140613.pdf')

    plt.figure(2)
    plt.clf()
    plot_image_for_source('ob150029', 10, 1e5)
    plt.savefig(paper_dir + 'img_ob150029.pdf')

    plt.figure(3)
    plt.clf()
    plot_image_for_source('ob150211', 12, 1e6)
    plt.savefig(paper_dir + 'img_ob150211.pdf')
    
    return
        

def plot_comparison_stars_all():
    plot_comparison_stars('ob140613')
    plot_comparison_stars('ob150029')
    plot_comparison_stars('ob150211')
    return

def plot_comparison_stars(target):
    ast_data_file = astrom_data[target]

    data = Table.read(ast_data_file)

    # Flip the coordinates to what we see on sky (+x increase to the East)
    data['x'] *= -1.0
    data['x0'] *= -1.0
    data['vx'] *= -1.0

    # Make a list of the source and the two nearby comparison stars (3 all together)
    targets = np.append([target], comp_stars[target])

    # Figure out the min/max of the times for these sources.
    tdx = np.where(data['name'] == target)[0][0]
    tmin = data['t'][tdx].min() - 0.5   # in days
    tmax = data['t'][tdx].max() + 0.5   # in days

    # Setup figure and color scales
    fig = plt.figure(1, figsize=(13, 6))
    plt.clf()
    grid = plt.GridSpec(5, 3, hspace=5, wspace=0.5)
    plt.subplots_adjust(left=0.12, right=0.86)

    cmap = plt.cm.viridis
    norm = plt.Normalize(vmin=tmin, vmax=tmax)
    smap = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    smap.set_array([])

    def plot_each_star(star_num, star_name):
        # Make two boxes for each star
        ax_sky = fig.add_subplot(grid[0:-2, star_num])
        ax_res = fig.add_subplot(grid[-2:, star_num])

        # Fetch the data
        tdx = np.where(data['name'] == star_name)[0][0]
        star = data[tdx]

        # Make the model curves
        tmod = np.arange(tmin, tmax, 0.1)
        xmod = star['x0'] + star['vx'] * (tmod - star['t0'])
        ymod = star['y0'] + star['vy'] * (tmod - star['t0'])
        xmode = np.hypot(star['x0e'], star['vxe'] * (tmod - star['t0']))
        ymode = np.hypot(star['y0e'], star['vye'] * (tmod - star['t0']))

        xmod_at_t = star['x0'] + star['vx'] * (star['t'] - star['t0'])
        ymod_at_t = star['y0'] + star['vy'] * (star['t'] - star['t0'])

        # Plot Positions on Sky
        sc = ax_sky.scatter(star['x'], star['y'], c=star['t'], cmap=cmap, norm=norm, s=5)
        ax_sky.errorbar(star['x'], star['y'], xerr=star['xe'], yerr=star['ye'],
                            ecolor=smap.to_rgba(star['t']), fmt='none')
        ax_sky.plot(xmod, ymod, 'k-', color='grey')
        ax_sky.plot(xmod + xmode, ymod + ymode, 'k--', color='grey')
        ax_sky.plot(xmod - xmode, ymod - ymode, 'k--', color='grey')
        ax_sky.set_aspect('equal', adjustable='datalim')

        # Figure out which axis has the bigger data range.
        xrng = np.abs(star['x'].max() - star['x'].min())
        yrng = np.abs(star['y'].max() - star['y'].min())
        if xrng > yrng:
            ax_sky.set_xlim(star['x'].min(), star['x'].max())
        else:
            ax_sky.set_ylim(star['y'].min(), star['y'].max())

        # Set labels
        ax_sky.invert_xaxis()
        ax_sky.set_title(star_name.upper())
        ax_sky.set_xlabel(r'$\Delta\alpha*$ (")')
        if star_num == 0:
            ax_sky.set_ylabel(r'$\Delta\delta$ (")')
            

        # Plot Residuals vs. Time
        xres = (star['x'] - xmod_at_t) * 1e3
        yres = (star['y'] - ymod_at_t) * 1e3
        xrese = star['xe'] * 1e3
        yrese = star['ye'] * 1e3
        ax_res.errorbar(star['t'], xres, yerr=xrese, fmt='r.', label=r'$\alpha*$')
        ax_res.errorbar(star['t'], yres, yerr=yrese, fmt='b.', label=r'$\delta$')
        ax_res.plot(tmod, xmod - xmod, 'r-')
        ax_res.plot(tmod, xmode*1e3, 'r--')
        ax_res.plot(tmod, -xmode*1e3, 'r--')
        ax_res.plot(tmod, ymod - ymod, 'b-')
        ax_res.plot(tmod, ymode*1e3, 'b--')
        ax_res.plot(tmod, -ymode*1e3, 'b--')
        ax_res.set_xlabel('Date (yr)')
        ax_res.set_ylim(-0.8, 0.8)
        if star_num == 0:
            ax_res.set_ylabel('Resid. (mas)')
        if star_num == 2:
            ax_res.legend(loc='right', bbox_to_anchor= (1.5, 0.5),
                              borderaxespad=0, frameon=True, numpoints=1,
                              handletextpad=0.1)
            # leg_ax = fig.add_axes([0.88, 0.12, 0.1, 0.1])
            # leg_ax.text(
            

        return sc

        
        
    sc = plot_each_star(0, targets[0])
    sc = plot_each_star(1, targets[1])
    sc = plot_each_star(2, targets[2])
    cb_ax = fig.add_axes([0.88, 0.41, 0.02, 0.49])
    plt.colorbar(sc, cax=cb_ax, label='Year')
    
    return

def plot_astrometry(target):
    data = munge_ob150211.getdata()

    best = {}
    best['mL'] = 10.386
    best['t0'] = 57211.845
    # best['xS0_E'] = 0.023101
    best['xS0_E'] = 0.022981
    # best['xS0_N'] = -0.113297
    best['xS0_N'] = -0.113357
    best['beta'] = -0.462895
    best['muL_E'] = -0.129050
    best['muL_N'] = -3.92588
    best['muS_E'] = 0.7187671
    best['muS_N'] = -1.77336
    best['dL'] = 5841.39
    best['dS'] = best['dL'] / 0.8772
    best['b_sff'] = 0.6451
    best['mag_src'] = 17.77
  
    # mymodel = model.PSPL_parallax(data['raL'], data['decL'],
    #                                    best['mL'], best['t0'], np.array([best['xS0_E'], best['xS0_N']]),
    #                                    best['beta'], np.array([best['muL_E'], best['muL_N']]),
    #                                    np.array([best['muS_E'], best['muS_N']]),
    #                                    best['dL'], best['dS'], best['b_sff'], best['mag_src'])
        
    fitter = model_fitter.PSPL_parallax_Solver(data, outputfiles_basename=pspl_ast_phot[target])
    fitter.load_mnest_results()
    mymodel = fitter.get_best_fit_model(use_median=True)

    #####
    # Astrometry on the sky
    #####
    plt.figure(2)
    plt.clf()

    # Data
    plt.errorbar(data['xpos']*1e3, data['ypos']*1e3,
                     xerr=data['xpos_err']*1e3, yerr=data['ypos_err']*1e3, fmt='k.')

    # 1 day sampling over whole range
    t_mod = np.arange(data['t_ast'].min(), data['t_ast'].max(), 1)
    
    # Model - usually from fitter
    pos_out = mymodel.get_astrometry(t_mod)
    plt.plot(pos_out[:, 0]*1e3, pos_out[:, 1]*1e3, 'r-')

    plt.gca().invert_xaxis()
    plt.xlabel(r'$\Delta \alpha^*$ (mas)')
    plt.ylabel(r'$\Delta \delta$ (mas)')
    plt.title('Input Data and Output Model')

    #####
    # astrometry vs. time
    #####
    plt.figure(3)
    plt.clf()
    plt.errorbar(data['t_ast'], data['xpos']*1e3,
                     yerr=data['xpos_err']*1e3, fmt='k.')
    plt.plot(t_mod, pos_out[:, 0]*1e3, 'r-')
    plt.xlabel('t - t0 (days)')
    plt.ylabel(r'$\Delta \alpha^*$ (mas)')
    plt.title('Input Data and Output Model')

    plt.figure(4)
    plt.clf()
    plt.errorbar(data['t_ast'], data['ypos']*1e3,
                     yerr=data['ypos_err']*1e3, fmt='k.')
    plt.plot(t_mod, pos_out[:, 1]*1e3, 'r-')
    plt.xlabel('t - t0 (days)')
    plt.ylabel(r'$\Delta \delta$ (mas)')
    plt.title('Input Data and Output Model')

    #####
    # Remove the unlensed motion (proper motion)
    # astrometry vs. time
    #####
    # Make the model unlensed points.
    p_mod_unlens_tdat = mymodel.get_astrometry_unlensed(data['t_ast'])
    x_mod_tdat = p_mod_unlens_tdat[:, 0]
    y_mod_tdat = p_mod_unlens_tdat[:, 1]
    x_no_pm = data['xpos'] - x_mod_tdat
    y_no_pm = data['ypos'] - y_mod_tdat

    # Make the dense sampled model for the same plot
    dp_tmod_unlens = mymodel.get_astrometry(t_mod) - mymodel.get_astrometry_unlensed(t_mod)
    x_mod_no_pm = dp_tmod_unlens[:, 0]
    y_mod_no_pm = dp_tmod_unlens[:, 1]

    # Prep some colorbar stuff
    cmap = plt.cm.viridis
    norm = plt.Normalize(vmin=data['t_ast'].min(), vmax=data['t_ast'].max())
    smap = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    smap.set_array([])

    # Average the data for the last three years.
    t_year = []
    x_year = []
    y_year = []
    xe_year = []
    ye_year = []
    
    t_dat_yr = multinest_plot.mmjd_to_year(data['t_ast'])

    min_year = np.floor(t_dat_yr.min())
    max_year = np.ceil(t_dat_yr.max())

    years = np.arange(min_year, max_year + 1, 1)
    for tt in range(len(years)-1):
        ii = np.where((years[tt] < t_dat_yr) & (t_dat_yr <= years[tt+1]))[0]
        
        if tt == 100:
            t_year = data['t_ast'][ii].data
            x_year = x_no_pm[ii]
            y_year = y_no_pm[ii]
            xe_year = data['xpos_err'][ii]
            ye_year = data['ypos_err'][ii]
        else:
            #wgts = np.hypot(data['xpos_err'][ii], data['ypos_err'][ii])
            wgts = (data['xpos_err'][ii] + data['ypos_err'][ii]) / 2.0
            t_avg, t_std = weighted_avg_and_std(data['t_ast'][ii], wgts )
            x_avg, x_std = weighted_avg_and_std(x_no_pm[ii], wgts )
            y_avg, y_std = weighted_avg_and_std(y_no_pm[ii], wgts )

            t_avg = data['t_ast'][ii].mean()
            t_std = data['t_ast'][ii].std()
            x_avg = x_no_pm[ii].mean()
            x_std = x_no_pm[ii].std()
            y_avg = y_no_pm[ii].mean()
            y_std = y_no_pm[ii].std()

            t_year = np.append( t_year, t_avg )
            x_year = np.append( x_year, x_avg )
            y_year = np.append( y_year, y_avg)
            xe_year = np.append( xe_year, x_std / np.sqrt(len(ii) - 1) )
            ye_year = np.append( ye_year, y_std / np.sqrt(len(ii) - 1) )


    t_year = np.array(t_year)
    x_year = np.array(x_year)
    y_year = np.array(y_year)
    xe_year = np.array(xe_year)
    ye_year = np.array(ye_year)
    print(t_year)
    print(x_year)
    
    plt.figure(5)
    plt.clf()
    plt.scatter(x_year*1e3, y_year*1e3, c=t_year,
                cmap=cmap, norm=norm, s=10)
    plt.errorbar(x_year*1e3, y_year*1e3,
                 xerr=xe_year*1e3, yerr=ye_year*1e3,
                 fmt='none', ecolor=smap.to_rgba(t_year))
    plt.scatter(x_mod_no_pm*1e3, y_mod_no_pm*1e3, c=t_mod, cmap=cmap, norm=norm, s=4)
    plt.gca().invert_xaxis()
    plt.axis('equal')
    plt.xlabel(r'$\Delta \alpha^*$ (mas)')
    plt.ylabel(r'$\Delta \delta$ (mas)')
    plt.colorbar()
    
    
    plt.figure(6)
    plt.clf()
    plt.scatter(x_no_pm*1e3, y_no_pm*1e3, c=data['t_ast'],
                cmap=cmap, norm=norm, s=10)
    plt.errorbar(x_no_pm*1e3, y_no_pm*1e3,
                 xerr=data['xpos_err']*1e3, yerr=data['ypos_err']*1e3,
                 fmt='none', ecolor=smap.to_rgba(data['t_ast']))
    plt.scatter(x_mod_no_pm*1e3, y_mod_no_pm*1e3, c=t_mod, cmap=cmap, norm=norm, s=4)
    plt.gca().invert_xaxis()
    plt.axis('equal')
    plt.xlabel(r'$\Delta \alpha^*$ (mas)')
    plt.ylabel(r'$\Delta \delta$ (mas)')
    plt.colorbar()

    return

def weighted_avg_and_std(values, weights):
    """
    Return the weighted average and standard deviation.

    values, weights -- Numpy ndarrays with the same shape.
    """
    average = np.average(values, weights=weights)
    # Fast and numerically precise:
    variance = np.average((values-average)**2, weights=weights)
    
    return (average, np.sqrt(variance))


def plot_ob150211_mass_posterior():
    """
    Lines are median, +/- 3 sigma.
    """

    fontsize1 = 18
    fontsize2 = 14

    tab = Table.read('/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/bb_.fits')
    mmax = tab['mL'].max()
    mmin = tab['mL'].min()

    plt.figure(1)
    plt.clf()
    plt.subplots_adjust(bottom = 0.15)
    xliml = 0.9 * mmin
    xlimu = 1.1 * mmax
    bins = np.logspace(np.log10(xliml), np.log10(xlimu), 500)

    n, b = np.histogram(tab['mL'], bins = bins, 
                        weights = tab['weights'], normed = True)

    n = norm_kde(n, 10.)
    b0 = 0.5 * (b[1:] + b[:-1])

    n, b, _ = plt.hist(b0, bins = b, weights = n)

    plt.xlabel('Lens Mass $(M_\odot)$', fontsize=fontsize1, labelpad=10)
    plt.xlim(xliml, xlimu)
    plt.ylabel('Relative probability', fontsize=fontsize1, labelpad=10)
    plt.xticks(fontsize=fontsize2)
    plt.yticks(fontsize=fontsize2)

    plt.xscale('log')

    ##########                                                                                                              
    # Calculate 3-sigma boundaries for mass limits.                                                                         
    ##########                                                                                                              
    sig1_hi = 0.682689
    sig1_lo = 1.0 - sig1_hi
    sig_med = 0.5
    sig2_hi = 0.9545
    sig2_lo = 1.0 - sig2_hi
    sig3_hi = 0.9973
    sig3_lo = 1.0 - sig3_hi

    quantiles = [sig3_lo, sig2_lo, sig1_lo, sig_med, sig1_hi, sig2_hi, sig3_hi]

    mass_quants = model_fitter.weighted_quantile(tab['mL'], quantiles,
                                                 sample_weight=tab['weights'])

    for qq in range(len(quantiles)):
        print( 'Mass at {0:.1f}% quantiles:  M = {1:5.2f}'.format(quantiles[qq]*100, mass_quants[qq]))

    ax = plt.axis()
    # plot median and +/- 3 sigma
    plt.axvline(mass_quants[0], color='k', linestyle='--')
    plt.axvline(mass_quants[3], color='k', linestyle='--')
    plt.axvline(mass_quants[-1], color='k', linestyle='--')
    plt.show()

    ##########                                                                                                           
    # Save figure                                                                                                     
    ##########                                                                                                            
    
#    outfile =  outdir + outfile
#    fileUtil.mkdir(outdir)
#    print( 'writing plot to file ' + outfile)
#
#    plt.savefig(outfile)

    return

def plot_ob150211_posterior_tE_piE_phot_astrom():
    span=None
    levels=None
    color='gray'
    plot_datapoints=False
    plot_density=True
    plot_contours=True
    no_fill_contours=False
    fill_contours=True
    contour_kwargs=None
    contourf_kwargs=None
    data_kwargs=None

    try:
        str_type = types.StringTypes
        float_type = types.FloatType
        int_type = types.IntType
    except:
        str_type = str
        float_type = float
        int_type = int
        
    """
    Basically the _hist2d function from dynesty, but with a few mods I made.
    https://github.com/joshspeagle/dynesty/blob/master/dynesty/plotting.py
    """

    tab = Table.read('/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/bb_.fits')

    x = tab['tE']
    y = (tab['piE_E']**2 + tab['piE_N']**2)**0.5
    weights = tab['weights']

    fig = plt.figure(1)
    plt.clf()
    ax = plt.gca()

    # Determine plotting bounds.
    data = [x, y]
    if span is None:
        span = [0.999999426697 for i in range(2)]
    span = list(span)
    if len(span) != 2:
        raise ValueError("Dimension mismatch between samples and span.")
    for i, _ in enumerate(span):
        try:
            xmin, xmax = span[i]
        except:
            q = [0.5 - 0.5 * span[i], 0.5 + 0.5 * span[i]]
            span[i] = dyutil.quantile(data[i], q, weights=weights)

    # The default "sigma" contour levels.
    if levels is None:
        levels = 1.0 - np.exp(-0.5 * np.arange(0.5, 2.1, 0.5) ** 2)

    # Color map for the density plot, over-plotted to indicate the
    # density of the points near the center.
    density_cmap = LinearSegmentedColormap.from_list(
        "density_cmap", [color, (1, 1, 1, 0)])

    # Color map used to hide the points at the high density areas.
    white_cmap = LinearSegmentedColormap.from_list(
        "white_cmap", [(1, 1, 1), (1, 1, 1)], N=2)

    # This "color map" is the list of colors for the contour levels if the
    # contours are filled.
    rgba_color = colorConverter.to_rgba(color)
    contour_cmap = [list(rgba_color) for l in levels] + [rgba_color]
    for i, l in enumerate(levels):
        contour_cmap[i][-1] *= float(i) / (len(levels)+1)
 
    xmax = x.max() 
    xmin = x.min()

    ymax = y.max() 
    ymin = y.min()

    xliml = 0.9 * xmin
    xlimu = 1.1 * xmax
    xbins = np.linspace(xliml, xlimu, 500)
   
    yliml = 0.9 * ymin
    ylimu = 1.1 * ymax
    ybins = np.linspace(yliml, ylimu, 500)

    # We'll make the 2D histogram to directly estimate the density.
    H, X, Y = np.histogram2d(x.flatten(), y.flatten(), bins=[xbins, ybins],
                             range=list(map(np.sort, span)),
                             weights=weights)
    # Smooth the results.
    H = norm_kde(H, [3, 3])
 
    # Compute the density levels.
    Hflat = H.flatten()
    inds = np.argsort(Hflat)[::-1]
    Hflat = Hflat[inds]
    sm = np.cumsum(Hflat)
    sm /= sm[-1]
    V = np.empty(len(levels))
    for i, v0 in enumerate(levels):
        try:
            V[i] = Hflat[sm <= v0][-1]
        except:
            V[i] = Hflat[0]
    V.sort()
    m = (np.diff(V) == 0)
    if np.any(m) and plot_contours:
        logging.warning("Too few points to create valid contours.")
        logging.warning("Make xnbin or ynbin bigger!!!!!!!")
    while np.any(m):
        V[np.where(m)[0][0]] *= 1.0 - 1e-4
        m = (np.diff(V) == 0)
    V.sort()

    # Compute the bin centers.
    X1, Y1 = 0.5 * (X[1:] + X[:-1]), 0.5 * (Y[1:] + Y[:-1])

    # Extend the array for the sake of the contours at the plot edges.
    H2 = H.min() + np.zeros((H.shape[0] + 4, H.shape[1] + 4))
    H2[2:-2, 2:-2] = H
    H2[2:-2, 1] = H[:, 0]
    H2[2:-2, -2] = H[:, -1]
    H2[1, 2:-2] = H[0]
    H2[-2, 2:-2] = H[-1]
    H2[1, 1] = H[0, 0]
    H2[1, -2] = H[0, -1]
    H2[-2, 1] = H[-1, 0]
    H2[-2, -2] = H[-1, -1]
    X2 = np.concatenate([X1[0] + np.array([-2, -1]) * np.diff(X1[:2]), X1,
                         X1[-1] + np.array([1, 2]) * np.diff(X1[-2:])])
    Y2 = np.concatenate([Y1[0] + np.array([-2, -1]) * np.diff(Y1[:2]), Y1,
                         Y1[-1] + np.array([1, 2]) * np.diff(Y1[-2:])])

    # Plot the data points.
    if plot_datapoints:
        if data_kwargs is None:
            data_kwargs = dict()
        data_kwargs["color"] = data_kwargs.get("color", color)
        data_kwargs["ms"] = data_kwargs.get("ms", 2.0)
        data_kwargs["mec"] = data_kwargs.get("mec", "none")
        data_kwargs["alpha"] = data_kwargs.get("alpha", 0.1)
        ax.plot(x, y, "o", zorder=-1, rasterized=True, **data_kwargs)

    # Plot the base fill to hide the densest data points.
    if (plot_contours or plot_density) and not no_fill_contours:
        ax.contourf(X2, Y2, H2.T, [V.min(), H.max()],
                    cmap=white_cmap, antialiased=False)

    if plot_contours and fill_contours:
        if contourf_kwargs is None:
            contourf_kwargs = dict()
        contourf_kwargs["colors"] = contourf_kwargs.get("colors", contour_cmap)
        contourf_kwargs["antialiased"] = contourf_kwargs.get("antialiased",
                                                             False)
        ax.contourf(X2, Y2, H2.T, np.concatenate([[0], V, [H.max()*(1+1e-4)]]),
                    **contourf_kwargs)

    # Plot the density map. This can't be plotted at the same time as the
    # contour fills.
    elif plot_density:
        ax.pcolor(X, Y, H.max() - H.T, cmap=density_cmap)

    # Plot the contour edge colors.
    if plot_contours:
        if contour_kwargs is None:
            contour_kwargs = dict()
        contour_kwargs["colors"] = contour_kwargs.get("colors", color)
        ax.contour(X2, Y2, H2.T, V, **contour_kwargs)

    ax.set_xlabel('$t_E$ (days)')
    ax.set_ylabel('$\pi_E$')

    ax.set_xlim(132, 144)
    ax.set_ylim(0, 0.04)

    plt.show()

    return

def plot_ob150211_posterior_deltac_piE_phot_astrom():
    span=None
    levels=None
    color='gray'
    plot_datapoints=False
    plot_density=True
    plot_contours=True
    no_fill_contours=False
    fill_contours=True
    contour_kwargs=None
    contourf_kwargs=None
    data_kwargs=None

    try:
        str_type = types.StringTypes
        float_type = types.FloatType
        int_type = types.IntType
    except:
        str_type = str
        float_type = float
        int_type = int
        
    """
    Basically the _hist2d function from dynesty, but with a few mods I made.
    https://github.com/joshspeagle/dynesty/blob/master/dynesty/plotting.py
    """

    tab = Table.read('/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/bb_.fits')

    x = tab['tE']
    y = (tab['piE_E']**2 + tab['piE_N']**2)**0.5
    weights = tab['weights']

    fig = plt.figure(1)
    plt.clf()
    ax = plt.gca()

    # Determine plotting bounds.
    data = [x, y]
    if span is None:
        span = [0.999999426697 for i in range(2)]
    span = list(span)
    if len(span) != 2:
        raise ValueError("Dimension mismatch between samples and span.")
    for i, _ in enumerate(span):
        try:
            xmin, xmax = span[i]
        except:
            q = [0.5 - 0.5 * span[i], 0.5 + 0.5 * span[i]]
            span[i] = dyutil.quantile(data[i], q, weights=weights)

    # The default "sigma" contour levels.
    if levels is None:
        levels = 1.0 - np.exp(-0.5 * np.arange(0.5, 2.1, 0.5) ** 2)

    # Color map for the density plot, over-plotted to indicate the
    # density of the points near the center.
    density_cmap = LinearSegmentedColormap.from_list(
        "density_cmap", [color, (1, 1, 1, 0)])

    # Color map used to hide the points at the high density areas.
    white_cmap = LinearSegmentedColormap.from_list(
        "white_cmap", [(1, 1, 1), (1, 1, 1)], N=2)

    # This "color map" is the list of colors for the contour levels if the
    # contours are filled.
    rgba_color = colorConverter.to_rgba(color)
    contour_cmap = [list(rgba_color) for l in levels] + [rgba_color]
    for i, l in enumerate(levels):
        contour_cmap[i][-1] *= float(i) / (len(levels)+1)
 
    xmax = x.max() 
    xmin = x.min()

    ymax = y.max() 
    ymin = y.min()

    xliml = 0.9 * xmin
    xlimu = 1.1 * xmax
    xbins = np.linspace(xliml, xlimu, 500)
   
    yliml = 0.9 * ymin
    ylimu = 1.1 * ymax
    ybins = np.linspace(yliml, ylimu, 500)

    # We'll make the 2D histogram to directly estimate the density.
    H, X, Y = np.histogram2d(x.flatten(), y.flatten(), bins=[xbins, ybins],
                             range=list(map(np.sort, span)),
                             weights=weights)
    # Smooth the results.
    H = norm_kde(H, [3, 3])
 
    # Compute the density levels.
    Hflat = H.flatten()
    inds = np.argsort(Hflat)[::-1]
    Hflat = Hflat[inds]
    sm = np.cumsum(Hflat)
    sm /= sm[-1]
    V = np.empty(len(levels))
    for i, v0 in enumerate(levels):
        try:
            V[i] = Hflat[sm <= v0][-1]
        except:
            V[i] = Hflat[0]
    V.sort()
    m = (np.diff(V) == 0)
    if np.any(m) and plot_contours:
        logging.warning("Too few points to create valid contours.")
        logging.warning("Make xnbin or ynbin bigger!!!!!!!")
    while np.any(m):
        V[np.where(m)[0][0]] *= 1.0 - 1e-4
        m = (np.diff(V) == 0)
    V.sort()

    # Compute the bin centers.
    X1, Y1 = 0.5 * (X[1:] + X[:-1]), 0.5 * (Y[1:] + Y[:-1])

    # Extend the array for the sake of the contours at the plot edges.
    H2 = H.min() + np.zeros((H.shape[0] + 4, H.shape[1] + 4))
    H2[2:-2, 2:-2] = H
    H2[2:-2, 1] = H[:, 0]
    H2[2:-2, -2] = H[:, -1]
    H2[1, 2:-2] = H[0]
    H2[-2, 2:-2] = H[-1]
    H2[1, 1] = H[0, 0]
    H2[1, -2] = H[0, -1]
    H2[-2, 1] = H[-1, 0]
    H2[-2, -2] = H[-1, -1]
    X2 = np.concatenate([X1[0] + np.array([-2, -1]) * np.diff(X1[:2]), X1,
                         X1[-1] + np.array([1, 2]) * np.diff(X1[-2:])])
    Y2 = np.concatenate([Y1[0] + np.array([-2, -1]) * np.diff(Y1[:2]), Y1,
                         Y1[-1] + np.array([1, 2]) * np.diff(Y1[-2:])])

    # Plot the data points.
    if plot_datapoints:
        if data_kwargs is None:
            data_kwargs = dict()
        data_kwargs["color"] = data_kwargs.get("color", color)
        data_kwargs["ms"] = data_kwargs.get("ms", 2.0)
        data_kwargs["mec"] = data_kwargs.get("mec", "none")
        data_kwargs["alpha"] = data_kwargs.get("alpha", 0.1)
        ax.plot(x, y, "o", zorder=-1, rasterized=True, **data_kwargs)

    # Plot the base fill to hide the densest data points.
    if (plot_contours or plot_density) and not no_fill_contours:
        ax.contourf(X2, Y2, H2.T, [V.min(), H.max()],
                    cmap=white_cmap, antialiased=False)

    if plot_contours and fill_contours:
        if contourf_kwargs is None:
            contourf_kwargs = dict()
        contourf_kwargs["colors"] = contourf_kwargs.get("colors", contour_cmap)
        contourf_kwargs["antialiased"] = contourf_kwargs.get("antialiased",
                                                             False)
        ax.contourf(X2, Y2, H2.T, np.concatenate([[0], V, [H.max()*(1+1e-4)]]),
                    **contourf_kwargs)

    # Plot the density map. This can't be plotted at the same time as the
    # contour fills.
    elif plot_density:
        ax.pcolor(X, Y, H.max() - H.T, cmap=density_cmap)

    # Plot the contour edge colors.
    if plot_contours:
        if contour_kwargs is None:
            contour_kwargs = dict()
        contour_kwargs["colors"] = contour_kwargs.get("colors", color)
        ax.contour(X2, Y2, H2.T, V, **contour_kwargs)

    ax.set_xlabel('$t_E$ (days)')
    ax.set_ylabel('$\pi_E$')

    ax.set_xlim(132, 144)
    ax.set_ylim(0, 0.04)

    plt.show()

    return


def plot_ob150211_posterior_tE_piE_phot_only():
    span=None
    levels=None
    color='gray'
    plot_datapoints=False
    plot_density=True
    plot_contours=True
    no_fill_contours=False
    fill_contours=True
    contour_kwargs=None
    contourf_kwargs=None
    data_kwargs=None

    try:
        str_type = types.StringTypes
        float_type = types.FloatType
        int_type = types.IntType
    except:
        str_type = str
        float_type = float
        int_type = int
        
    """
    Basically the _hist2d function from dynesty, but with a few mods I made.
    https://github.com/joshspeagle/dynesty/blob/master/dynesty/plotting.py
    """

    tab = Table.read('/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/3_fit_phot_parallax/u0_plusminus/aa_.fits')
    
    x = tab['tE']
    y = (tab['piE_E']**2 + tab['piE_N']**2)**0.5
    weights = tab['weights']

    fig = plt.figure(2)
    plt.clf()
    ax = plt.gca()

    # Determine plotting bounds.
    data = [x, y]
    if span is None:
        span = [0.999999426697 for i in range(2)]
    span = list(span)
    if len(span) != 2:
        raise ValueError("Dimension mismatch between samples and span.")
    for i, _ in enumerate(span):
        try:
            xmin, xmax = span[i]
        except:
            q = [0.5 - 0.5 * span[i], 0.5 + 0.5 * span[i]]
            span[i] = dyutil.quantile(data[i], q, weights=weights)

    # The default "sigma" contour levels.
    if levels is None:
        levels = 1.0 - np.exp(-0.5 * np.arange(0.5, 2.1, 0.5) ** 2)

    # Color map for the density plot, over-plotted to indicate the
    # density of the points near the center.
    density_cmap = LinearSegmentedColormap.from_list(
        "density_cmap", [color, (1, 1, 1, 0)])

    # Color map used to hide the points at the high density areas.
    white_cmap = LinearSegmentedColormap.from_list(
        "white_cmap", [(1, 1, 1), (1, 1, 1)], N=2)

    # This "color map" is the list of colors for the contour levels if the
    # contours are filled.
    rgba_color = colorConverter.to_rgba(color)
    contour_cmap = [list(rgba_color) for l in levels] + [rgba_color]
    for i, l in enumerate(levels):
        contour_cmap[i][-1] *= float(i) / (len(levels)+1)
 
    xmax = x.max() 
    xmin = x.min()

    ymax = y.max() 
    ymin = y.min()

    xliml = 0.9 * xmin
    xlimu = 1.1 * xmax
    xbins = np.linspace(xliml, xlimu, 500)
   
    yliml = 0.9 * ymin
    ylimu = 1.1 * ymax
    ybins = np.linspace(yliml, ylimu, 500)

    # We'll make the 2D histogram to directly estimate the density.
    H, X, Y = np.histogram2d(x.flatten(), y.flatten(), bins=[xbins, ybins],
                             range=list(map(np.sort, span)),
                             weights=weights)
    # Smooth the results.
    H = norm_kde(H, [3, 3])
 
    # Compute the density levels.
    Hflat = H.flatten()
    inds = np.argsort(Hflat)[::-1]
    Hflat = Hflat[inds]
    sm = np.cumsum(Hflat)
    sm /= sm[-1]
    V = np.empty(len(levels))
    for i, v0 in enumerate(levels):
        try:
            V[i] = Hflat[sm <= v0][-1]
        except:
            V[i] = Hflat[0]
    V.sort()
    m = (np.diff(V) == 0)
    if np.any(m) and plot_contours:
        logging.warning("Too few points to create valid contours.")
        logging.warning("Make xnbin or ynbin bigger!!!!!!!")
    while np.any(m):
        V[np.where(m)[0][0]] *= 1.0 - 1e-4
        m = (np.diff(V) == 0)
    V.sort()

    # Compute the bin centers.
    X1, Y1 = 0.5 * (X[1:] + X[:-1]), 0.5 * (Y[1:] + Y[:-1])

    # Extend the array for the sake of the contours at the plot edges.
    H2 = H.min() + np.zeros((H.shape[0] + 4, H.shape[1] + 4))
    H2[2:-2, 2:-2] = H
    H2[2:-2, 1] = H[:, 0]
    H2[2:-2, -2] = H[:, -1]
    H2[1, 2:-2] = H[0]
    H2[-2, 2:-2] = H[-1]
    H2[1, 1] = H[0, 0]
    H2[1, -2] = H[0, -1]
    H2[-2, 1] = H[-1, 0]
    H2[-2, -2] = H[-1, -1]
    X2 = np.concatenate([X1[0] + np.array([-2, -1]) * np.diff(X1[:2]), X1,
                         X1[-1] + np.array([1, 2]) * np.diff(X1[-2:])])
    Y2 = np.concatenate([Y1[0] + np.array([-2, -1]) * np.diff(Y1[:2]), Y1,
                         Y1[-1] + np.array([1, 2]) * np.diff(Y1[-2:])])

    # Plot the data points.
    if plot_datapoints:
        if data_kwargs is None:
            data_kwargs = dict()
        data_kwargs["color"] = data_kwargs.get("color", color)
        data_kwargs["ms"] = data_kwargs.get("ms", 2.0)
        data_kwargs["mec"] = data_kwargs.get("mec", "none")
        data_kwargs["alpha"] = data_kwargs.get("alpha", 0.1)
        ax.plot(x, y, "o", zorder=-1, rasterized=True, **data_kwargs)

    # Plot the base fill to hide the densest data points.
    if (plot_contours or plot_density) and not no_fill_contours:
        ax.contourf(X2, Y2, H2.T, [V.min(), H.max()],
                    cmap=white_cmap, antialiased=False)

    if plot_contours and fill_contours:
        if contourf_kwargs is None:
            contourf_kwargs = dict()
        contourf_kwargs["colors"] = contourf_kwargs.get("colors", contour_cmap)
        contourf_kwargs["antialiased"] = contourf_kwargs.get("antialiased",
                                                             False)
        ax.contourf(X2, Y2, H2.T, np.concatenate([[0], V, [H.max()*(1+1e-4)]]),
                    **contourf_kwargs)

    # Plot the density map. This can't be plotted at the same time as the
    # contour fills.
    elif plot_density:
        ax.pcolor(X, Y, H.max() - H.T, cmap=density_cmap)

    # Plot the contour edge colors.
    if plot_contours:
        if contour_kwargs is None:
            contour_kwargs = dict()
        contour_kwargs["colors"] = contour_kwargs.get("colors", color)
        ax.contour(X2, Y2, H2.T, V, **contour_kwargs)

    ax.set_xlabel('$t_E$ (days)')
    ax.set_ylabel('$\pi_E$')

    ax.set_xlim(100, 160)
    ax.set_ylim(0, 0.12)

    plt.show()

    return
 
def make_ob150211_tab():
    """
    Documentation: https://github.com/JohannesBuchner/MultiNest
    We want post_separate and not summary, since it separates out the two modes.
    """

    # Get the photometry-only data
    mnest_dir_phot_only = '/g/lu/scratch/jlu/work/microlens/OB150211/a_2019_05_04/notes/3_fit_phot_parallax/u0_plusminus/'
    mnest_root_phot_only = 'aa_'
    best_arr_phot_only = np.loadtxt(mnest_dir_phot_only + mnest_root_phot_only + 'summary.txt')
    best_phot_only_sol1 = best_arr_phot_only[1][14:21]
    logZ_phot_only_sol1 = best_arr_phot_only[1][28]
    maxL_phot_only_sol1 = best_arr_phot_only[1][29]
    best_phot_only_sol2 = best_arr_phot_only[2][14:21]
    logZ_phot_only_sol2 = best_arr_phot_only[2][28]
    maxL_phot_only_sol2 = best_arr_phot_only[2][29]

    # FIXME: Make these files and make sure they match up with the old indices.
    mnest_tab_phot_only_sol1 = np.loadtxt(mnest_dir_phot_only + mnest_root_phot_only + 'mode0.dat')
    mnest_tab_phot_only_sol2 = np.loadtxt(mnest_dir_phot_only + mnest_root_phot_only + 'mode1.dat')
    
    # Get the phot+astrom data
    mnest_dir_phot_astr = '/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/'
    mnest_root_phot_astr = 'bb_'
    best_arr_phot_astr = np.loadtxt(mnest_dir_phot_astr + mnest_root_phot_astr + 'summary.txt')
    best_phot_astr_sol1 = best_arr_phot_astr[1][42:63]
    logZ_phot_astr_sol1 = best_arr_phot_astr[1][84]
    maxL_phot_astr_sol1 = best_arr_phot_astr[1][85]
    best_phot_astr_sol2 = best_arr_phot_astr[2][42:63]
    logZ_phot_astr_sol2 = best_arr_phot_astr[2][84]
    maxL_phot_astr_sol2 = best_arr_phot_astr[2][85]

    # FIXME: Make these files and make sure they match up with the old indices.
    mnest_tab_phot_astr_sol1 = np.loadtxt(mnest_dir_phot_astr + mnest_root_phot_astr + 'mode0.dat')
    mnest_tab_phot_astr_sol2 = np.loadtxt(mnest_dir_phot_astr + mnest_root_phot_astr + 'mode1.dat')

    # SUPER DUPER STUPID... have to find the separation of the two different modes 
    # in the post_separate file by hand and hardcode in...........
    # Get 2sigma errors
    phot_only_pars1, phot_only_med_vals1 = model_fitter.quantiles(mnest_tab_phot_only_sol1)
    phot_only_pars2, phot_only_med_vals2 = model_fitter.quantiles(mnest_tab_phot_only_sol2)

    phot_astr_pars1, phot_astr_med_vals1 = model_fitter.quantiles(mnest_tab_phot_astr_sol1)
    phot_astr_pars2, phot_astr_med_vals2 = model_fitter.quantiles(mnest_tab_phot_astr_sol2)

    params_list = ['t0', 'u0_amp', 'tE', 
                   'piE_E', 'piE_N', 'b_sff', 'mag_src',
                   'mL', 'xS0_E', 'xS0_N', 'beta',
                   'muL_E', 'muL_N', 'muS_E', 'muS_N',
                   'dL', 'dL_dS', 'dS', 'thetaE', 'muRel_E', 'muRel_N']

    params = {'t0' : [r'$t_0$ (MJD)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'u0_amp' : [r'$u_0$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'tE' : [r'$t_E$ (days)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'piE_E' : [r'$\pi_{E,E}$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'], 
              'piE_N' : [r'$\pi_{E,N}$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'b_sff' : [r'$b_{SFF}$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'mag_src' : [r'$I_{OGLE}$ (mag)', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'], 
              'mL' : [r'$M_L (M_\odot$)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'xS0_E' : [r"$x_{S,0,E}$ ($''$)", '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'xS0_N' : [r"$x_{S,0,N}$ ($''$)", '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'beta' : [r'$\beta$ (mas)', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'muL_E' : [r'$\mu_{L,E}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muL_N' : [r'$\mu_{L,N}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muS_E' : [r'$\mu_{S,E}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muS_N' : [r'$\mu_{S,N}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'dL' : [r'$d_L$ (pc)', '${0:.0f}^{{+{1:.0f}}}_{{-{2:.0f}}}$'],
              'dS' : [r'$d_S$ (pc) $^\dagger$', '${0:.0f}^{{+{1:.0f}}}_{{-{2:.0f}}}$'],
              'dL_dS' : [r'$d_L/d_S$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'thetaE' : [r'$\theta_E$ (mas)^\dagger', '${0:.1f}^{{+{1:.1f}}}_{{-{2:.1f}}}$'],
              'muRel_E' : [r'$\mu_{rel,E}$ (mas/yr)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muRel_N' : [r'$\mu_{rel,N}$ (mas/yr)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$']}

    output = open('ob150211_param_fits_table.txt', 'w')
    for pp in params_list:
        p = params[pp]
        if pp in phot_only_pars1:
            phot_only_sol1 = p[1].format(phot_only_med_vals1[pp][0],
                                         phot_only_med_vals1[pp][2],
                                         phot_only_med_vals1[pp][1])
            phot_only_sol2 = p[1].format(phot_only_med_vals2[pp][0],
                                         phot_only_med_vals2[pp][2],
                                         phot_only_med_vals2[pp][1])
        else:
            phot_only_sol1 = '--'
            phot_only_sol2 = '--'
        if pp in phot_astr_pars1:
            phot_astr_sol1 = p[1].format(phot_astr_med_vals1[pp][0],
                                         phot_astr_med_vals1[pp][2],
                                         phot_astr_med_vals1[pp][1])
            phot_astr_sol2 = p[1].format(phot_astr_med_vals2[pp][0],
                                         phot_astr_med_vals2[pp][2],
                                         phot_astr_med_vals2[pp][1])
        else:
            phot_astr_sol1 = '--'
            phot_astr_sol2 = '--'

        output.write(p[0] + ' & ' + phot_only_sol1 + ' & ' + phot_astr_sol2 + ' & ' + phot_only_sol2 + ' & ' + phot_astr_sol1 + ' \\\\\n')

    output.write('log$\mathcal{Z}$' + ' & ' + '{:.2f}'.format(logZ_phot_only_sol1) + '& ' + '{:.2f}'.format(logZ_phot_astr_sol2) + ' & ' + '{:.2f}'.format(logZ_phot_only_sol2) + ' & ' + '{:.2f}'.format(logZ_phot_astr_sol1) + ' \\\\\n')

    output.close()

def make_ob150211_tab_old():
    # FIXMES:
    # 1. Don't use multinest_utils.load_mnest_results_to_tab
    """
    Documentation: https://github.com/JohannesBuchner/MultiNest
    We want post_separate and not summary, since it separates out the two modes.
    """

    # Get the photometry-only data
    best_arr_phot_only = np.loadtxt('/g/lu/scratch/jlu/work/microlens/OB150211/a_2019_05_04/notes/3_fit_phot_parallax/u0_plusminus/aa_summary.txt')
    best_phot_only_sol1 = best_arr_phot_only[1][14:21]
    logZ_phot_only_sol1 = best_arr_phot_only[1][28]
    maxL_phot_only_sol1 = best_arr_phot_only[1][29]
    best_phot_only_sol2 = best_arr_phot_only[2][14:21]
    logZ_phot_only_sol2 = best_arr_phot_only[2][28]
    maxL_phot_only_sol2 = best_arr_phot_only[2][29]
    mnest_tab_phot_only = multinest_utils.load_mnest_results_to_tab('/g/lu/scratch/jlu/work/microlens/OB150211/a_2019_05_04/notes/3_fit_phot_parallax/u0_plusminus/aa_post_separate')
    
    # Get the phot+astrom data
    best_arr_phot_astr = np.loadtxt('/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/bb_summary.txt')
    best_phot_astr_sol1 = best_arr_phot_astr[1][42:63]
    logZ_phot_astr_sol1 = best_arr_phot_astr[1][84]
    maxL_phot_astr_sol1 = best_arr_phot_astr[1][85]
    best_phot_astr_sol2 = best_arr_phot_astr[2][42:63]
    logZ_phot_astr_sol2 = best_arr_phot_astr[2][84]
    maxL_phot_astr_sol2 = best_arr_phot_astr[2][85]
    mnest_tab_phot_astr = multinest_utils.load_mnest_results_to_tab('/g/lu/scratch/jlu/work/microlens/OB150211/a_2019_05_04/notes/4_fit_phot_astrom_parallax/bb_post_separate')

    # SUPER DUPER STUPID... have to find the separation of the two different modes 
    # in the post_separate file by hand and hardcode in...........
    # Get 2sigma errors
    phot_only_pars1, phot_only_med_vals1 = model_fitter.quantiles(mnest_tab_phot_only[:9387])
    phot_only_pars2, phot_only_med_vals2 = model_fitter.quantiles(mnest_tab_phot_only[9387:])

    phot_astr_pars1, phot_astr_med_vals1 = model_fitter.quantiles(mnest_tab_phot_astr[:13041])
    phot_astr_pars2, phot_astr_med_vals2 = model_fitter.quantiles(mnest_tab_phot_astr[13041:])

#    params_list = ['mL', 't0', 'xS0_E', 'xS0_N', 'beta',
#                   'muL_E', 'muL_N', 'muS_E', 'muS_N',
#                   'dL', 'dL_dS', 'dS', 'thetaE',
#                   'muRel_E', 'muRel_N', 'u0_amp', 'tE', 
#                   'piE_E', 'piE_N', 'b_sff', 'mag_src']

    params_list = ['t0', 'u0_amp', 'tE', 
                   'piE_E', 'piE_N', 'b_sff', 'mag_src',
                   'mL', 'xS0_E', 'xS0_N', 'beta',
                   'muL_E', 'muL_N', 'muS_E', 'muS_N',
                   'dL', 'dL_dS', 'dS', 'thetaE', 'muRel_E', 'muRel_N']

    params = {'t0' : [r'$t_0$ (MJD)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'u0_amp' : [r'$u_0$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'tE' : [r'$t_E$ (days)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'piE_E' : [r'$\pi_{E,E}$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'], 
              'piE_N' : [r'$\pi_{E,N}$ $^\dagger$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'b_sff' : [r'$b_{SFF}$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'mag_src' : [r'$I_{OGLE}$ (mag)', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'], 
              'mL' : [r'$M_L (M_\odot$)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'xS0_E' : [r"$x_{S,0,E}$ ($''$)", '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'xS0_N' : [r"$x_{S,0,N}$ ($''$)", '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'beta' : [r'$\beta$ (mas)', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'muL_E' : [r'$\mu_{L,E}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muL_N' : [r'$\mu_{L,N}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muS_E' : [r'$\mu_{S,E}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muS_N' : [r'$\mu_{S,N}$ (mas/yr)', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'dL' : [r'$d_L$ (pc)', '${0:.0f}^{{+{1:.0f}}}_{{-{2:.0f}}}$'],
              'dS' : [r'$d_S$ (pc) $^\dagger$', '${0:.0f}^{{+{1:.0f}}}_{{-{2:.0f}}}$'],
              'dL_dS' : [r'$d_L/d_S$', '${0:.3f}^{{+{1:.3f}}}_{{-{2:.3f}}}$'],
              'thetaE' : [r'$\theta_E$ (mas)^\dagger', '${0:.1f}^{{+{1:.1f}}}_{{-{2:.1f}}}$'],
              'muRel_E' : [r'$\mu_{rel,E}$ (mas/yr)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$'],
              'muRel_N' : [r'$\mu_{rel,N}$ (mas/yr)$^\dagger$', '${0:.2f}^{{+{1:.2f}}}_{{-{2:.2f}}}$']}

    output = open('ob150211_param_fits_table.txt', 'w')
    for pp in params_list:
        p = params[pp]
        if pp in phot_only_pars1:
            phot_only_sol1 = p[1].format(phot_only_med_vals1[pp][0],
                                         phot_only_med_vals1[pp][2],
                                         phot_only_med_vals1[pp][1])
            phot_only_sol2 = p[1].format(phot_only_med_vals2[pp][0],
                                         phot_only_med_vals2[pp][2],
                                         phot_only_med_vals2[pp][1])
        else:
            phot_only_sol1 = '--'
            phot_only_sol2 = '--'
        if pp in phot_astr_pars1:
            phot_astr_sol1 = p[1].format(phot_astr_med_vals1[pp][0],
                                         phot_astr_med_vals1[pp][2],
                                         phot_astr_med_vals1[pp][1])
            phot_astr_sol2 = p[1].format(phot_astr_med_vals2[pp][0],
                                         phot_astr_med_vals2[pp][2],
                                         phot_astr_med_vals2[pp][1])
        else:
            phot_astr_sol1 = '--'
            phot_astr_sol2 = '--'

        output.write(p[0] + ' & ' + phot_only_sol1 + ' & ' + phot_astr_sol2 + ' & ' + phot_only_sol2 + ' & ' + phot_astr_sol1 + ' \\\\\n')

    output.write('log$\mathcal{Z}$' + ' & ' + '{:.2f}'.format(logZ_phot_only_sol1) + '& ' + '{:.2f}'.format(logZ_phot_astr_sol2) + ' & ' + '{:.2f}'.format(logZ_phot_only_sol2) + ' & ' + '{:.2f}'.format(logZ_phot_astr_sol1) + ' \\\\\n')

    output.close()

def plot_ob150211_phot():
    data = munge_ob150211.getdata()

    mnest_dir = '/u/jlu/work/microlens/OB150211/a_2019_05_04/notes/3_fit_phot_parallax/u0_plusminus/'
    mnest_root = 'aa_'

    fitter = model_fitter.PSPL_phot_parallax_Solver(data,
                                                    outputfiles_basename = mnest_dir + mnest_root)

    tab_phot_par = fitter.load_mnest_results()

    multinest_plot.plot_phot_fit(data, mnest_dir, mnest_root, outdir=mnest_dir, parallax=True)

    return
