import pylab as py
import numpy as np
# import pymultinest
import scipy.stats
import atpy
import math
import pdb

def make_random_data():
    # Dist 1
    rand_norm = scipy.stats.norm()
    
    # Dist 2
    rand_uni = scipy.stats.uniform(loc=-5, scale=7)
    
    # Generate 100 objects with normal distribution, p(yng) = 1 (e.g. yng = norm)
    rand_set_1 = rand_norm.rvs(size=100)
    #rand_set_1 = scipy.stats.powerlaw.rvs(2.0, size=100)
    p_yng_1 = np.ones(len(rand_set_1), dtype=float)

    # Generate 50 objects with uniform distribution, p(yng) = 0 (e.g. yng = norm)
    rand_set_2 = rand_uni.rvs(size=100)
    p_yng_2 = np.zeros(len(rand_set_2), dtype=float)

    # Generate another 50 each, but assign non-zero p(yng)
    rand_set_3 = rand_norm.rvs(size=50)
    tmp_p_yng_3 = rand_norm.pdf(rand_set_3)
    tmp_p_old_3 = rand_uni.pdf(rand_set_3)
    p_yng_3 = tmp_p_yng_3 / (tmp_p_yng_3 + tmp_p_old_3)

    rand_set_4 = rand_uni.rvs(size=50)
    tmp_p_yng_4 = rand_norm.pdf(rand_set_4)
    tmp_p_old_4 = rand_uni.pdf(rand_set_4)
    p_yng_4 = tmp_p_yng_4 / (tmp_p_yng_4 + tmp_p_old_4)

    # Gather all the data and p(yng) togeter into a single data set
    data = np.concatenate([rand_set_1, rand_set_2, rand_set_3, rand_set_4])
    p_yng = np.concatenate([p_yng_1, p_yng_2, p_yng_3, p_yng_4])

    bins = np.arange(-5, 5, 1)

    py.clf()
    py.hist(data, histtype='step', label='Unweighted', bins=bins)
    py.hist(data, histtype='step', weights=p_yng, label='Yng', bins=bins)
    py.hist(data, histtype='step', weights=(1.0 - p_yng), label='Old', bins=bins)
    py.legend(loc='upper left')
    py.savefig('/u/jlu/work/stats/test_prob_yng/random_data.png')

    out = atpy.Table()
    out.add_column('mydata', data)
    out.add_column('pyng', p_yng, dtype=np.float32)
    out.write('/u/jlu/work/stats/test_prob_yng/random_data.txt',
              type='ascii', overwrite=True)
                   
def test_membership_prob(test):
    """
    A self-contained test to figure out what we should be doing
    with the membership information (prob(yng)) in the bayesian
    analysis.
    """
    print 'Performing Test: ', test, test == 'mix'

    tab = atpy.Table('/u/jlu/work/stats/test_prob_yng/random_data.txt', type='ascii')
    data = tab.mydata
    p_yng = tab.pyng

    # Now we are going to run a multinest fitting program.
    # We will fit only the gaussian distribution but we need
    # to account for the probability of membership.
    def priors(cube, ndim, nparams):
        return

    def random_alpha(randNum):
        alpha_min = 0.1
        alpha_max = 5
        alpha_diff = alpha_max - alpha_min
        alpha = scipy.stats.uniform.ppf(randNum, loc=alpha_min, scale=alpha_diff)
        log_prob_alpha = scipy.stats.uniform.logpdf(alpha, loc=alpha_min, scale=alpha_diff)

        return alpha, log_prob_alpha

    def random_mean(randNum):
        mean_min = -1.0
        mean_max = 1.0
        mean_diff = mean_max - mean_min
        mean = scipy.stats.uniform.ppf(randNum, loc=mean_min, scale=mean_diff)
        log_prob_mean = scipy.stats.uniform.logpdf(mean, loc=mean_min, scale=mean_diff)
        
        return mean, log_prob_mean

    def random_sigma(randNum):
        sigma_min = 0.0
        sigma_max = 2.0
        sigma_diff = sigma_max - sigma_min
        sigma = scipy.stats.uniform.ppf(randNum, loc=sigma_min, scale=sigma_diff)
        log_prob_sigma = scipy.stats.uniform.logpdf(sigma, loc=sigma_min, scale=sigma_diff)

        return sigma, log_prob_sigma

    def random_uni_edge(randNum, edge_min, edge_max):
        edge_diff = edge_max - edge_min
        edge = scipy.stats.uniform.ppf(randNum, loc=edge_min, scale=edge_diff)
        log_prob_edge = scipy.stats.uniform.logpdf(edge, loc=edge_min, scale=edge_diff)

        return edge, log_prob_edge

    def logLikePL1(cube, ndim, nparams):
        alpha, log_prob_alpha = random_alpha(cube[0])
        cube[0] = alpha

        L_i = scipy.stats.powerlaw.pdf(data, alpha) * p_yng
        log_L = np.log10( L_i ).sum()
        log_L += log_prob_alpha

        return log_L

    def logLikePL2(cube, ndim, nparams):
        alpha, log_prob_alpha = random_alpha(cube[0])
        cube[0] = alpha

        L_i = scipy.stats.powerlaw.pdf(data, alpha)
        log_L = (p_yng * np.log10( L_i )).sum()
        log_L += log_prob_alpha

        return log_L

    def logLike1(cube, ndim, nparams):
        mean, log_prob_mean = random_mean(cube[0])
        cube[0] = mean

        sigma, log_prob_sigma = random_sigma(cube[1])
        cube[1] = sigma

        idx = np.where(p_yng != 0)[0]

        L_i = scipy.stats.norm.pdf(data[idx], loc=mean, scale=sigma) * p_yng[idx]
        log_L = np.log10( L_i ).sum()
        log_L += log_prob_mean
        log_L += log_prob_sigma

        return log_L

    def logLike2(cube, ndim, nparams):
        mean, log_prob_mean = random_mean(cube[0])
        cube[0] = mean

        sigma, log_prob_sigma = random_sigma(cube[1])
        cube[1] = sigma

        L_i = scipy.stats.norm.pdf(data, loc=mean, scale=sigma)
        log_L = (p_yng * np.log10( L_i )).sum()
        log_L += log_prob_mean
        log_L += log_prob_sigma

        return log_L

    def logLike3(cube, ndim, nparams):
        mean, log_prob_mean = random_mean(cube[0])
        cube[0] = mean

        sigma, log_prob_sigma = random_sigma(cube[1])
        cube[1] = sigma

        tmp = np.random.uniform(size=len(data))
        idx = np.where(tmp <= p_yng)
        L_i = scipy.stats.norm.pdf(data[idx], loc=mean, scale=sigma)
        log_L = np.log10( L_i ).sum()
        log_L += log_prob_mean
        log_L += log_prob_sigma

        return log_L

    def logLike4(cube, ndim, nparams):
        mean, log_prob_mean = random_mean(cube[0])
        cube[0] = mean

        sigma, log_prob_sigma = random_sigma(cube[1])
        cube[1] = sigma

        uni_l, log_prob_uni_l = random_uni_edge(cube[2], -10, -1)
        cube[2] = uni_l

        uni_h, log_prob_uni_h = random_uni_edge(cube[3], 0, 10)
        cube[3] = uni_h


        L_i_m1 = scipy.stats.norm.pdf(data, loc=mean, scale=sigma)
        L_i_m2 = scipy.stats.uniform.pdf(data, loc=uni_l, scale=(uni_h - uni_l))
        L_i = (p_yng * L_i_m1) + ((1 - p_yng) * L_i_m2)
        log_L = np.log10( L_i ).sum()
        log_L += log_prob_mean
        log_L += log_prob_sigma
        log_L += log_prob_uni_l
        log_L += log_prob_uni_h

        return log_L

    num_params = 2
    num_dims = 2
    ev_tol = 0.7
    samp_eff = 0.5
    n_live_points = 300

    #Now run all 3 tests.

    if test == 'multi':
        outroot = '/u/jlu/work/stats/test_prob_yng/multi_'
        pymultinest.run(logLike1, priors, num_dims, n_params=num_params,
                        outputfiles_basename=outroot,
                        verbose=True, resume=False,
                        evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                        n_live_points=n_live_points)

    if test == 'power':
        outroot = '/u/jlu/work/stats/test_prob_yng/power_'
        pymultinest.run(logLike2, priors, num_dims, n_params=num_params,
                        outputfiles_basename=outroot,
                        verbose=True, resume=False,
                        evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                        n_live_points=n_live_points)

    if test == 'mix':
        num_params = 4
        num_dims = 4
        n_clust_param = num_dims - 1
        outroot = '/u/jlu/work/stats/test_prob_yng/mix_'
        pymultinest.run(logLike4, priors, num_dims, n_params=num_params,
                        outputfiles_basename=outroot,
                        verbose=True, resume=False,
                        evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                        n_live_points=n_live_points)

    if test == 'mc':
        outroot = '/u/jlu/work/stats/test_prob_yng/mc_'
        pymultinest.run(logLike3, priors, num_dims, n_params=num_params,
                        outputfiles_basename=outroot,
                        verbose=True, resume=False,
                        evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                        n_clustering_params=n_clust_param,
                        n_live_points=n_live_points)


def plot_test_membership_prob(out_file_root):
    from jlu.gc.imf import multinest as m
    outroot = '/u/jlu/work/stats/test_prob_yng/' + out_file_root + '_'

    tab = atpy.Table(outroot + '.txt', type='ascii')

    # First column is the weights
    weights = tab['col1']
    logLike = tab['col2'] / -2.0
    
    # Now delete the first two rows
    tab.remove_columns(('col1', 'col2'))

    # Rename the parameter columns. This is hard-coded to match the
    # above run() function.
    tab.rename_column('col3', 'mean')
    tab.rename_column('col4', 'sigma')

    m.pair_posterior(tab, weights, outfile=outroot+'posteriors.png')


def test_bernoulli_prob():
    """
    A self-contained test to figure out why the Bernoulli distribution
    isn't working in the likelihood.
    """
    print 'Starting'
    ####################
    # Some random powerlaw populations to play with.
    ####################
    rand_set_1 = scipy.stats.powerlaw.rvs(3.0, size=5000)

    # Apply a linear completeness correction
    def comp(xval, x0=0.6, a=30):
        dx = xval - x0
        denom = np.sqrt(1.0 + a**2 * dx**2)
        f = 0.5 * (1.0 - ((a * dx) / denom))

        return f

    comp_at_rand = comp(rand_set_1)
    detect_rand = scipy.stats.uniform.rvs(size=len(rand_set_1))
    detect_idx = np.where(detect_rand <= comp_at_rand)[0]

    observed_set_1 = rand_set_1[detect_idx]
    data = observed_set_1
    N_obs = len(data)
    print 'Number of observed stars'

    # Now we are going to run a multinest fitting program.
    # We will fit only the gaussian distribution but we need
    # to account for the probability of membership.
    def priors(cube, ndim, nparams):
        return

    print 'Random Number generators'
    alpha_min = 1.0
    alpha_max = 4.0
    alpha_diff = alpha_max - alpha_min
    alpha_gen = scipy.stats.uniform(loc=alpha_min, scale=alpha_diff)

    log_N_min = np.log(1000)
    log_N_max = np.log(50000)
    log_N_diff = log_N_max - log_N_min
    log_N_gen = scipy.stats.uniform(loc=log_N_min, scale=log_N_diff)
    
    N_min = 1000
    N_max = 50000
    N_diff = N_max - N_min
    N_gen = scipy.stats.uniform(loc=N_min, scale=N_diff)

    def random_alpha(randNum):
        alpha = alpha_gen.ppf(randNum)
        log_prob_alpha = alpha_gen.logpdf(alpha)
        return alpha, log_prob_alpha

    def random_N(randNum):
        # log_N = log_N_gen.ppf(randNum)
        # N = math.e**log_N
        # log_prob_N = log_N_gen.logpdf(log_N)

        N = N_gen.ppf(randNum)
        log_prob_N = N_gen.logpdf(N)
        return N, log_prob_N


    # Bins for histograms of PDF
    bin_width = 0.025
    bins = np.arange(0, 1+bin_width, bin_width)
    bin_centers = bins[:-1] + (bin_width / 2.0)

    # Completeness at bin centers
    print 'completeness'
    comp_at_bins = comp(bin_centers)
    incomp_at_bins = 1.0 - comp_at_bins

    def logLike(cube, ndim, nparams):
        alpha, log_prob_alpha = random_alpha(cube[0])
        cube[0] = alpha

        N, log_prob_N = random_N(cube[1])
        cube[1] = N

        if N_obs >= N:
            return -np.Inf

        # Make a simulated data set - similar to what we do when we don't
        # have the analytic expression for the luminosity function.
        sim_plaw = scipy.stats.powerlaw(alpha)

        # Bin it up to make a normalized PDF
        sim_cdf = sim_plaw.cdf(bins)
        sim_pdf = np.diff(sim_cdf)
        sim_pdf_norm = sim_pdf / (sim_pdf * bin_width).sum()

        ##########
        # Parts of the Likelihood
        ##########
        # Binomial coefficient:
        log_L_binom_coeff = scipy.special.gammaln(N + 1)
        log_L_binom_coeff -= scipy.special.gammaln(N_obs + 1)
        log_L_binom_coeff -= scipy.special.gammaln(N - N_obs + 1)

        # Undetected part
        tmp = (sim_pdf_norm * incomp_at_bins * bin_width).sum()
        log_L_non_detect = (N - N_obs) * np.log(tmp)

        # Detected part
        log_L_detect = 0.0

        for ii in range(N_obs):
            # Find the closest bin in the PDF
            dx = np.abs(data[ii] - bin_centers)
            idx = dx.argmin()

            L_i = comp_at_bins[idx] * sim_pdf_norm[idx]

            if L_i == 0.0:
                log_L_detect += -np.Inf
            else:
                log_L_detect += np.log(L_i)

        log_L = log_L_binom_coeff + log_L_non_detect + log_L_detect
        log_L += log_prob_alpha
        log_L += log_prob_N

        cube[2] = log_L_binom_coeff
        cube[3] = log_L_non_detect
        cube[4] = log_L_detect

        return log_L

    def logLike2(cube, ndim, nparams):
        alpha, log_prob_alpha = random_alpha(cube[0])
        cube[0] = alpha

        N, log_prob_N = random_N(cube[1])
        cube[1] = N

        # Make a simulated data set - similar to what we do when we don't
        # have the analytic expression for the luminosity function.
        sim_plaw = scipy.stats.powerlaw(alpha)

        # Bin it up to make a normalized PDF
        sim_cdf = sim_plaw.cdf(bins)
        sim_pdf = np.diff(sim_cdf) * N
        sim_pdf *= comp_at_bins
        sim_pdf_norm = sim_pdf / (sim_pdf * bin_width).sum()

        N_obs_sim = sim_pdf.sum()

        ##########
        # Parts of the Likelihood
        ##########
        # Number of stars part
        log_L_N_obs = scipy.stats.poisson.logpmf(N_obs, N_obs_sim)
        
        # Detected part
        log_L_detect = 0.0

        for ii in range(N_obs):
            # Find the closest bin in the PDF
            dx = np.abs(data[ii] - bin_centers)
            idx = dx.argmin()

            L_i = sim_pdf_norm[idx]

            if L_i == 0.0:
                log_L_detect += -np.Inf
            else:
                log_L_detect += np.log(L_i)

        log_L = log_L_detect + log_L_N_obs
        log_L += log_prob_alpha
        log_L += log_prob_N

        cube[2] = log_L_detect
        cube[3] = log_L_N_obs
        cube[4] = N_obs_sim

        return log_L

    num_params = 5
    num_dims = 2
    n_clust_param = num_dims - 1
    ev_tol = 0.7
    samp_eff = 0.5
    n_live_points = 300

    # Now run the tests.
    # outroot = '/u/jlu/work/stats/test_bernoulli/multi_bern_2.8_3.2'
    # print 'running multinest'
    # pymultinest.run(logLike, priors, num_dims, n_params=num_params,
    #                 outputfiles_basename=outroot,
    #                 verbose=True, resume=False,
    #                 evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
    #                 n_live_points=n_live_points)

    outroot = '/u/jlu/work/stats/test_bernoulli/multi_plaw_1.0_4.0_'
    print 'running multinest'
    pymultinest.run(logLike2, priors, num_dims, n_params=num_params,
                    outputfiles_basename=outroot,
                    verbose=True, resume=False,
                    evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                    n_live_points=n_live_points)


def plot_test_bernoulli(out_file_root):
    outroot = '/u/jlu/work/stats/test_bernoulli/' + out_file_root #+ '_'

    tab = atpy.Table(outroot + '.txt', type='ascii')

    tab['col2'] /= -2.0

    tab.rename_column('col1', 'weights')
    tab.rename_column('col2', 'logLike')
    tab.rename_column('col3', 'alpha')
    tab.rename_column('col4', 'N')
    tab.rename_column('col5', 'logL_b')
    tab.rename_column('col6', 'logL_nd')
    tab.rename_column('col7', 'logL_d')

    py.figure(1)
    py.clf()
    bins_alpha = np.arange(1.0, 5.0, 0.01)
    (n, b, p) = py.hist(tab.alpha, weights=tab.weights, histtype='step', bins=bins_alpha)
    py.ylim(0, 1.1 * n.max())
    idx = np.where(n > 0)[0]
    py.xlim(b[idx[0]-1], b[idx[-1]+1])
    py.axvline(3.0)
    py.xlabel('alpha')
    py.savefig(outroot + 'posterior_alpha.png')

    py.figure(2)
    py.clf()
    bins_N = np.arange(1000, 50000, 100)
    (n, b, p) = py.hist(tab.N, weights=tab.weights, histtype='step', bins=bins_N)
    py.ylim(0, 1.1 * n.max())
    idx = np.where(n > 0)[0]
    py.xlim(b[idx[0]-1], b[idx[-1]+1])
    py.axvline(10000)
    py.ylabel('N')
    py.savefig(outroot + 'posterior_N.png')

    H, xedges, yedges = np.histogram2d(tab.alpha, tab.N, weights=tab.weights,
                                       bins=[bins_alpha, bins_N])

    py.figure(3)
    py.clf()
    extent = [yedges[0], yedges[-1], xedges[0], xedges[-1]]
    py.imshow(H, extent=extent, interpolation='nearest')
    py.colorbar()
    py.axis('tight')
    idx = np.where(H > 0)
    print bins_N[idx[1][0]], bins_N[idx[1][-1]]
    print bins_alpha[idx[0][0]], bins_alpha[idx[0][-1]]
    py.xlim(bins_N[idx[1][0]], bins_N[idx[1][-1]])
    py.ylim(bins_alpha[idx[0][0]], bins_alpha[idx[0][-1]])
    py.xlabel('N')
    py.ylabel('alpha')
    py.savefig(outroot + 'posterior_2d.png')


def test_amplitude():
    """
    A self-contained test to figure out whether we need to include the
    amplitude as a free parameter. Compare results with the test_bernoulli
    logLike2 output.
    """
    print 'Starting'
    ####################
    # Some random powerlaw populations to play with.
    ####################
    rand_set_1 = scipy.stats.powerlaw.rvs(3.0, size=5000)

    # Apply a linear completeness correction
    def comp(xval, x0=0.6, a=30):
        dx = xval - x0
        denom = np.sqrt(1.0 + a**2 * dx**2)
        f = 0.5 * (1.0 - ((a * dx) / denom))

        return f

    comp_at_rand = comp(rand_set_1)
    detect_rand = scipy.stats.uniform.rvs(size=len(rand_set_1))
    detect_idx = np.where(detect_rand <= comp_at_rand)[0]

    observed_set_1 = rand_set_1[detect_idx]
    data = observed_set_1
    N_obs = len(data)
    print 'Number of observed stars'

    # Now we are going to run a multinest fitting program.
    # We will fit only the gaussian distribution but we need
    # to account for the probability of membership.
    def priors(cube, ndim, nparams):
        return

    print 'Random Number generators'
    alpha_min = 1.0
    alpha_max = 4.0
    alpha_diff = alpha_max - alpha_min
    alpha_gen = scipy.stats.uniform(loc=alpha_min, scale=alpha_diff)

    def random_alpha(randNum):
        alpha = alpha_gen.ppf(randNum)
        log_prob_alpha = alpha_gen.logpdf(alpha)
        return alpha, log_prob_alpha

    # Bins for histograms of PDF
    bin_width = 0.025
    bins = np.arange(0, 1+bin_width, bin_width)
    bin_centers = bins[:-1] + (bin_width / 2.0)

    # Completeness at bin centers
    print 'completeness'
    comp_at_bins = comp(bin_centers)
    incomp_at_bins = 1.0 - comp_at_bins

    def logLike(cube, ndim, nparams):
        alpha, log_prob_alpha = random_alpha(cube[0])
        cube[0] = alpha

        # Make a simulated data set - similar to what we do when we don't
        # have the analytic expression for the luminosity function.
        sim_plaw = scipy.stats.powerlaw(alpha)

        # Bin it up to make a normalized PDF
        sim_cdf = sim_plaw.cdf(bins)
        sim_pdf = np.diff(sim_cdf)
        sim_pdf *= comp_at_bins
        sim_pdf_norm = sim_pdf / (sim_pdf * bin_width).sum()
        
        N = N_obs / sim_pdf.sum()

        cube[1] = N

        ##########
        # Parts of the Likelihood
        ##########
        # Detected part
        log_L_detect = 0.0

        for ii in range(N_obs):
            # Find the closest bin in the PDF
            dx = np.abs(data[ii] - bin_centers)
            idx = dx.argmin()

            L_i = sim_pdf_norm[idx]

            if L_i == 0.0:
                log_L_detect += -np.Inf
            else:
                log_L_detect += np.log(L_i)

        log_L = log_L_detect
        log_L += log_prob_alpha

        cube[2] = log_L_detect

        return log_L

    num_params = 3
    num_dims = 1
    n_clust_param = num_dims - 1
    ev_tol = 0.7
    samp_eff = 0.5
    n_live_points = 300

    # Now run the tests.
    outroot = '/u/jlu/work/stats/test_bernoulli/multi_noamp_'
    print 'running multinest'
    pymultinest.run(logLike, priors, num_dims, n_params=num_params,
                    outputfiles_basename=outroot,
                    verbose=True, resume=False,
                    evidence_tolerance=ev_tol, sampling_efficiency=samp_eff,
                    n_live_points=n_live_points)


def plot_test_amplitude(out_file_root):
    outroot = '/u/jlu/work/stats/test_bernoulli/' + out_file_root #+ '_'

    tab = atpy.Table(outroot + '.txt', type='ascii')

    tab['col2'] /= -2.0

    tab.rename_column('col1', 'weights')
    tab.rename_column('col2', 'logLike')
    tab.rename_column('col3', 'alpha')
    tab.rename_column('col4', 'N')
    tab.rename_column('col5', 'logL_d')

    py.figure(1)
    py.clf()
    bins_alpha = np.arange(1.0, 5.0, 0.01)
    (n, b, p) = py.hist(tab.alpha, weights=tab.weights, histtype='step', bins=bins_alpha)
    py.ylim(0, 1.1 * n.max())
    idx = np.where(n > 0)[0]
    py.xlim(b[idx[0]-1], b[idx[-1]+1])
    py.axvline(3.0)
    py.xlabel('alpha')
    py.savefig(outroot + 'posterior_alpha.png')

    py.figure(2)
    py.clf()
    bins_N = np.arange(1000, 50000, 100)
    (n, b, p) = py.hist(tab.N, weights=tab.weights, histtype='step', bins=bins_N)
    py.ylim(0, 1.1 * n.max())
    idx = np.where(n > 0)[0]
    py.xlim(b[idx[0]-1], b[idx[-1]+1])
    py.axvline(5000)
    py.ylabel('N')
    py.savefig(outroot + 'posterior_N.png')

    H, xedges, yedges = np.histogram2d(tab.alpha, tab.N, weights=tab.weights,
                                       bins=[bins_alpha, bins_N])

    py.figure(3)
    py.clf()
    extent = [yedges[0], yedges[-1], xedges[0], xedges[-1]]
    py.imshow(H, extent=extent, interpolation='nearest')
    py.colorbar()
    py.axis('tight')
    idx = np.where(H > 0)
    print bins_N[idx[1][0]], bins_N[idx[1][-1]]
    print bins_alpha[idx[0][0]], bins_alpha[idx[0][-1]]
    py.xlim(bins_N[idx[1][0]], bins_N[idx[1][-1]])
    py.ylim(bins_alpha[idx[0][0]], bins_alpha[idx[0][-1]])
    py.xlabel('N')
    py.ylabel('alpha')
    py.savefig(outroot + 'posterior_2d.png')


def test_imf_sampling(totalMass=1.0e4, imfSlope=2.35):
    minMass = 1.0
    maxMass = 150.0

    n_runs = 100
    log_mass_bins = np.arange(0, 2.5, 0.2)
    hists1 = np.zeros((n_runs, len(log_mass_bins)-1), dtype=float)
    hists2 = np.zeros((n_runs, len(log_mass_bins)-1), dtype=float)
    
    for nn in range(n_runs):
        mass1, isMulti1, compMass1 = sample_imf(totalMass, 
                                                minMass, maxMass, 
                                                imfSlope)
        mass2, isMulti2, compMass2 = sample_imf_var_max_mass(totalMass, 
                                                             minMass, maxMass, 
                                                             imfSlope)
        H1, b1 = np.histogram(np.log10(mass1), bins=log_mass_bins)
        H2, b2 = np.histogram(np.log10(mass2), bins=log_mass_bins)

        hists1[nn] = H1
        hists2[nn] = H2

    bin_cent = log_mass_bins[:-1] + np.diff(log_mass_bins)

    py.figure(1)
    py.clf()
    for nn in range(n_runs):
        py.semilogy(bin_cent, hists1[nn], 'k-', alpha=0.2)
        py.semilogy(bin_cent, hists2[nn], 'r-', alpha=0.2)
    py.ylim(1, 1200)
    py.savefig('test_imf_sampling_all_m%d_a%.2f.png' % (totalMass, imfSlope))


    means1 = hists1.mean(axis=0)
    stds1 = hists1.std(axis=0)
    means2 = hists2.mean(axis=0)
    stds2 = hists2.std(axis=0)

    py.figure(2)
    py.clf()
    py.errorbar(bin_cent, means1, yerr=stds1, fmt='ko')
    py.errorbar(bin_cent, means2, yerr=stds2, fmt='ro')
    py.gca().set_yscale('log')
    py.ylim(1, 1200)
    py.xlim(0, 2.5)
    py.savefig('test_imf_sampling_avg_m%d_a%.2f.png' % (totalMass, imfSlope))


defaultAKs = 2.7
defaultDist = 8000
defaultFilter = 'Kp'
defaultMFamp = 0.44
defaultMFindex = 0.51
defaultCSFamp = 0.50
defaultCSFindex = 0.45
defaultCSFmax = 3

def sample_imf(totalMass, minMass, maxMass, imfSlope,
               multiMFamp=defaultMFamp, multiMFindex=defaultMFindex,
               multiCSFamp=defaultCSFamp, multiCSFindex=defaultCSFindex,
               multiCSFmax=defaultCSFmax,
               makeMultiples=True, multiQindex=-0.4, multiQmin=0.01,
               verbose=False):
    """
    Randomly sample from an IMF of the specified slope and mass
    limits until the desired total mass is reached. The maximum
    stellar mass is not allowed to exceed the total cluster mass.
    The simulated total mass will not be exactly equivalent to the
    desired total mass; but we will take one star above or below
    (whichever brings us closer to the desired total) the desired
    total cluster mass break point.

    IMF Slope is 2.35 for Salpeter.
    """
    if (maxMass > totalMass) and verbose:
        print 'sample_imf: Setting maximum allowed mass to %d' % \
            (totalMass)
        maxMass = totalMass

    # p(m) = A * m^-imfSlope
    # Setup useful variables
    nG = 1 - imfSlope  # This is also -Gamma, hence nG name

    if imfSlope != 1:
        A =  nG / (maxMass**nG - minMass**nG)
    else:
        A = 1.0 / (math.log(maxMass) - math.log(minMass))

    # Generative function for primary masses
    def cdf_inv_not_1(x, minMass, maxMass, nG):
        return (x * (maxMass**nG - minMass**nG) + minMass**nG)**(1.0/nG)

    # This is the special case for alpha = 1.0
    def cdf_inv_1(x, minMass, maxMass, nG):
        return minMass * (maxMass / minMass)**x

    # Generative function for companion mass ratio (q = m_comp/m_primary)
    def q_cdf_inv(x, qLo, beta):
        b = 1.0 + beta
        return (x * (1.0 - qLo**b) + qLo**b)**(1.0/b)

    # First estimate the mean number of stars expected
    if imfSlope != 1:
        if imfSlope != 2: 
            nGp1 = 1 + nG
            meanMass = A * (maxMass**nGp1 - minMass**nGp1) / nGp1
        else:
            meanMass = A * (math.log(maxMass) - math.log(minMass))

        cdf_inv = cdf_inv_not_1
    else:
        meanMass = A * (maxMass - minMass)
        cdf_inv = cdf_inv_1

    meanNumber = round(totalMass / meanMass)

    simTotalMass = 0
    newStarCount = round(meanNumber)
    if not makeMultiples:
        newStarCount *= 1.1

    masses = np.array([], dtype=float)
    isMultiple = np.array([], dtype=bool)
    compMasses = []
    systemMasses = np.array([], dtype=float)

    def binary_properties(mass):
        # Multiplicity Fraction
        mf = multiMFamp * mass**multiMFindex
        mf[mf > 1] = 1

        # Companion Star Fraction
        csf = multiCSFamp * mass**multiCSFindex
        csf[csf > 3] = multiCSFmax

        return mf, csf

    loopCnt = 0

    while simTotalMass < totalMass:
        # Generate a random distribution 20% larger than
        # the number we expect to need.
        uniX = np.random.rand(newStarCount)

        # Convert into the IMF from the inverted CDF
        newMasses = cdf_inv(uniX, minMass, maxMass, nG)

        if makeMultiples:
            compMasses = [[] for ii in range(len(newMasses))]

            # Determine the multiplicity of every star
            MF, CSF = binary_properties(newMasses)
            newIsMultiple = np.random.rand(newStarCount) < MF
            newSystemMasses = newMasses.copy()
        
            # Calculate number and masses of companions
            for ii in range(len(newMasses)):
                if newIsMultiple[ii]:
                    n_comp = 1 + np.random.poisson((CSF[ii]/MF[ii]) - 1)
                    q_values = q_cdf_inv(np.random.rand(n_comp), multiQmin, multiQindex)
                    m_comp = q_values * newMasses[ii]

                    # Only keep companions that are more than the minimum mass
                    mdx = np.where(m_comp >= minMass)
                    compMasses[ii] = m_comp[mdx]
                    newSystemMasses[ii] += compMasses[ii].sum()

                    # Double check for the case when we drop all companions.
                    # This happens a lot near the minimum allowed mass.
                    if len(mdx) == 0:
                        newIsMultiple[ii] == False

            newSimTotalMass = newSystemMasses.sum()
            isMultiple = np.append(isMultiple, newIsMultiple)
            systemMasses = np.append(systemMasses, newSystemMasses)
        else:
            newSimTotalMass = newMasses.sum()

        # Append to our primary masses array
        masses = np.append(masses, newMasses)

        if (loopCnt >= 0) and verbose:
            print 'sample_imf: Loop %d added %.2e Msun to previous total of %.2e Msun' % \
                (loopCnt, newSimTotalMass, simTotalMass)

        simTotalMass += newSimTotalMass
        newStarCount = meanNumber * 0.1  # increase by 20% each pass
        loopCnt += 1
        
    # Make a running sum of the system masses
    if makeMultiples:
        massCumSum = systemMasses.cumsum()
    else:
        massCumSum = masses.cumsum()

    # Find the index where we are closest to the desired
    # total mass.
    #idx = np.abs(massCumSum - totalMass).argmin()
    idx = np.where(massCumSum <= totalMass)[0][-1]

    masses = masses[:idx+1]

    if makeMultiples:
        systemMasses = systemMasses[:idx+1]
        isMultiple = isMultiple[:idx+1]
        compMasses = compMasses[:idx+1]
    else:
        isMultiple = np.zeros(len(masses), dtype=bool)

    return (masses, isMultiple, compMasses)


def sample_imf_var_max_mass(totalMass, minMass, maxMass, imfSlope,
                            multiMFamp=defaultMFamp, 
                            multiMFindex=defaultMFindex,
                            multiCSFamp=defaultCSFamp, 
                            multiCSFindex=defaultCSFindex,
                            multiCSFmax=defaultCSFmax,
                            makeMultiples=True, 
                            multiQindex=-0.4, multiQmin=0.01,
                            verbose=False):

    # p(m) = A * m^-imfSlope
    # Setup useful variables
    nG = 1 - imfSlope  # This is also -Gamma, hence nG name

    if imfSlope != 1:
        A =  nG / (maxMass**nG - minMass**nG)
    else:
        A = 1.0 / (math.log(maxMass) - math.log(minMass))

    # Generative function for primary masses
    def cdf_inv_not_1(x, minMass, maxMass, nG):
        return (x * (maxMass**nG - minMass**nG) + minMass**nG)**(1.0/nG)

    # This is the special case for alpha = 1.0
    def cdf_inv_1(x, minMass, maxMass, nG):
        return minMass * (maxMass / minMass)**x

    # Generative function for companion mass ratio (q = m_comp/m_primary)
    def q_cdf_inv(x, qLo, beta):
        b = 1.0 + beta
        return (x * (1.0 - qLo**b) + qLo**b)**(1.0/b)

    # First estimate the mean number of stars expected
    if imfSlope != 1:
        if imfSlope != 2: 
            nGp1 = 1 + nG
            meanMass = A * (maxMass**nGp1 - minMass**nGp1) / nGp1
        else:
            meanMass = A * (math.log(maxMass) - math.log(minMass))

        cdf_inv = cdf_inv_not_1
    else:
        meanMass = A * (maxMass - minMass)
        cdf_inv = cdf_inv_1

    meanNumber = round(totalMass / meanMass)

    simTotalMass = 0
    newStarCount = round(meanNumber)
    if not makeMultiples:
        newStarCount *= 1.1

    masses = np.array([], dtype=float)
    isMultiple = np.array([], dtype=bool)
    compMasses = []
    systemMasses = np.array([], dtype=float)

    def binary_properties(mass):
        # Multiplicity Fraction
        mf = multiMFamp * mass**multiMFindex
        if mf > 1:
            mf = 1

        # Companion Star Fraction
        csf = multiCSFamp * mass**multiCSFindex
        if csf > 3:
            csf = multiCSFmax

        return mf, csf

    loopCnt = 0
    simTotalMass = 0

    while simTotalMass < totalMass:
        # Determine the allowable maximum mass given the 
        # already generated masses
        simMaxMass = totalMass - simTotalMass

        # Generate a single star
        uniX = np.random.rand()
        newMass = cdf_inv(uniX, minMass, simMaxMass, nG)

        if makeMultiples:
            compMasses = []

            # Determine the multiplicity of every star
            MF, CSF = binary_properties(newMass)
            newIsMultiple = np.random.rand() < MF
            newSystemMass = newMass
        
            # Calculate number and masses of companions
            if newIsMultiple:
                n_comp = 1 + np.random.poisson((CSF/MF) - 1)
                q_values = q_cdf_inv(np.random.rand(n_comp), multiQmin, multiQindex)
                m_comp = q_values * newMass

                # Only keep companions that are more than the minimum mass
                mdx = np.where(m_comp >= minMass)
                compMass = m_comp[mdx]
                newSystemMass += compMass.sum()
                
                # Double check for the case when we drop all companions.
                # This happens a lot near the minimum allowed mass.
                if len(mdx) == 0:
                    newIsMultiple == False

            simTotalMass += newSystemMass
            isMultiple = np.append(isMultiple, newIsMultiple)
            systemMasses = np.append(systemMasses, newSystemMass)
        else:
            simTotalMass += newMass

        # Append to our primary masses array
        masses = np.append(masses, newMass)
        loopCnt += 1
        
    # Make a running sum of the system masses
    if makeMultiples:
        massCumSum = systemMasses.cumsum()
    else:
        massCumSum = masses.cumsum()

    if not makeMultiples:
        isMultiple = np.zeros(len(masses), dtype=bool)

    return (masses, isMultiple, compMasses)
    
