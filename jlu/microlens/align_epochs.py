import numpy as np
import os
import sys
import string
import residuals
from astropy.table import Table
import pylab as py
import scipy.stats

def align_loop(root='/Users/jlu/work/microlens/OB120169/', prefix='analysis', target='ob120169', 
               date='2015_09_14', sourceDir='analysis_ob120169_2015_09_14',
               transforms=[3,4,5], magCuts=[18,20,22], weightings=[1,2,3,4],
               Nepochs='5', overwrite=False, nMC=1,
               makePlots=False, DoAlign=False, letterStart=0):
    """
    root -- The main directory for both the data and analysis sub-directories.
    prefix --
    target -- 
    date --
    sourceDir -- The directory containing the label.dat file.
    transforms -- The align -a flags to iterate over.
    magCuts -- The align -?
    weightings -- The align -?

    Code originally written by Evan Sinukoff. Modified by J.R. Lu
    """
    
    # Read in the label.dat file. Target must be in first row of label.dat file.
    labelFile = target + '_label.dat'
    data = Table.read(root + sourceDir + '/source_list/'+ labelFile, format='ascii')
    transposed = zip(*data)

    # Decide which sources we are going to be omitting for the align bootstrap.
    Nlines = len(data)
    if nMC > 1:
        Nomit = 1     #Do MC w/ half-sampling
    else:
        Nomit = Nlines  # Do jackknife
    
    a, m, w, Ntrials = TrialPars(Nomit, transforms, magCuts, weightings)
    DirNames = GetDirNames(Ntrials, target, date, prefix, Nomit = Nomit,
                           letterStart=letterStart, nMC=nMC)

    if DoAlign == True:
		n = -1
		for i in range(Ntrials / (Nomit + 1)):    # loop over letters
			for j in range(Nomit + 1):            # loop over lines in label.dat
				os.chdir(root)
				n = n + 1
				NewDirPath = root + DirNames[n]
				if (os.path.isdir(NewDirPath) == 0 or overwrite == True):    
					try:
						os.mkdir(DirNames[n])
					except: 
						os.system('rm -r ' + DirNames[n])
						os.mkdir(DirNames[n])
                        
					print 'Creating new directory: ' + NewDirPath
					os.chdir(DirNames[n])
					os.system('mkdir align lis plots points_d polyfit_d scripts source_list')
					os.system('cp ../' + sourceDir + '/lis/*radTrim* lis')
					v = [0]*13  #13 columns in label.dat file
					if j != 0:
						os.system('cp ../' + sourceDir + '/source_list/' + labelFile + ' source_list/temp.dat')
						for c in range(13):
							temp = np.genfromtxt('source_list/temp.dat', 
							usecols=(c), comments=None, 
							unpack=True, dtype=None) 
							v[c] = temp
						v[11][j-1] = 0
						v[11][0] = 0   #target will always be omitted
						f_handle = file('source_list/temp.dat', 'a')
						
						np.savetxt('source_list/'+ target + '_label.dat', np.c_[v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],v[9],v[10],v[11],v[12]], fmt='%13s')
						f_handle.close()
						os.system('rm -f source_list/temp.dat')
						
					else:
						os.system('cp ../' + sourceDir + '/source_list/' + labelFile + ' source_list/')
						
					 
					os.system('cp ../' + sourceDir + '/align/*Input* align') 
					os.chdir('align')
					os.system('java align -a ' + str(a[n]) + ' -m ' + str(m[n]) + ' -w ' + str(w[n]) + ' -R 3 -n ' +
                               str(nMC) + ' -p -N ../source_list/' + target + '_label.dat InputAlign_' + target + '.list')
					os.system('java trim_align -e ' + Nepochs + ' -r align_t -N ../source_list/' + target +
							  '_label.dat -f ../points_d/ -p align')
					os.system('polyfit -d 1 -linear -i align_t -points ../points_d/ -o ../polyfit_d/fit')
				
				else:       
					if os.path.isdir(NewDirPath) == 1: 
						print 'Directory ' + NewDirPath + ' already exists.  Did not overwrite.'
			
    os.chdir(root)
    if makePlots == True:
		print 'Plotting...'
		AlignPlot(root=root, DirNames=DirNames, NjackKnifes=Nomit, m=m)
    


def AlignPlot(root, DirNames, NjackKnifes, m): 
	   
    Ndirs = len(DirNames)
    n=-1
    for i in range(Ndirs/(NjackKnifes+1)):
        for j in range(NjackKnifes+1):
            n=n+1
            print DirNames[n]
            os.chdir(root+DirNames[n])
            makeResPlot(root=root, DirName=DirNames[n])  # Comment these out as needed
            makeVectorPlot(root=root, DirName=DirNames[n], magCut = m[n]) # Comment these out as needed
            if j != 0:
                velX, velY = GetVel(root, DirNames[n])
                velXarr.append(velX)
                velYarr.append(velY)
                if j == NjackKnifes:
                    NewDirPath = root+DirNames[n]
                    str1,str2 = NewDirPath.split('omit_') 
                    PlotVelSig(str1 + 'omit_0/plots', velXarr, velYarr)   
            else:
                velXarr = []
                velYarr = []

    velXlist = []
    velYlist = []
    velSigXlist = []
    velSigYlist = []
    for i in range(Ndirs/2):
        print DirNames[2*i+1]
        velXarr, velYarr = GetVel(root, DirNames[2*i+1])
        print len(velXarr)
        velSigXarr, velSigYarr, Nstars = GetVelSigDist(root, DirNames[2*i+1])
        velXlist.append(velXarr)
        velYlist.append(velYarr)
        velSigXlist.append(velSigXarr)
        velSigYlist.append(velSigYarr)
    relErrX = []
    relErrY = []
    print len(velXlist), Nstars
    print velXlist
    for i in range(Ndirs/2):
        for j in range(Ndirs/2):
            for k in range (Nstars):
                print i, j, k
                if i != j:
                    deltaVx = velXlist[i][k] - velXlist[j][k]
                    sigVx = np.sqrt(velSigXlist[i][k]**2. + velSigXlist[j][k]**2.)
                    relErrX.append(deltaVx/sigVx)
                    deltaVy = velYlist[i][k] - velYlist[j][k]
                    sigVy = np.sqrt(velSigYlist[i][k]**2. + velSigYlist[j][k]**2.)
                    relErrY.append(deltaVy/sigVy)
    PlotVelSigDist(root + DirNames[0], relErrX, relErrY)
    print 'plotting Velocity error distribution (sigma) in directory: ' + root + DirNames[0]


def TrialPars(Nomit, transforms, magCuts, weightings):
    Ntrans = len(transforms)
    Nmags = len(magCuts)
    Nweights = len(weightings)
    
    
    Ntrials = Ntrans*Nmags*Nweights*(Nomit+1)
    a = []
    m = []
    w = []
    
    for i in range(Ntrans):   
        for j in range(Nmags):
           for k in range(Nweights):
               for l in range(Nomit+1):
                   a.append(transforms[i])
                   m.append(magCuts[j])
                   w.append(weightings[k])
    
    return a, m, w, Ntrials     



def GetDirNames(Ntrials, target, date, prefix, letterStart, Nomit, nMC):


    alphabet = string.lowercase
    DirNames = []
    
    for i in range(Ntrials/(Nomit+1)):
        for j in range(Nomit+1):
            indOmit = j
            # if Ntrials/(Nomit+1) < len(alphabet):     
#                 if alphabet[i+letterStart] == 'a':
#                 	DirNames.append(prefix + '_' + target + '_' + date + '_omit_' + str(indOmit) )
#             	else:
#                 	DirNames.append(prefix + '_' + target + '_' + date + 'a' + alphabet[i+letterStart] + '_omit_' + str(indOmit))
#             else:
#            if i >=4:
#                letterStart = 12
            letter1 = alphabet[int((i+letterStart)/(len(alphabet)))]
            letter2 =  alphabet[((i+letterStart) % len(alphabet))] 
            if letter1 == 'a' and letter2 == 'a':
                DirNames.append(prefix + '_' + target + '_' + date + '_' + 'MC' + str(nMC) + '_omit_' + str(indOmit))
            else:
				DirNames.append(prefix + '_' + target + '_' + date + letter1 + letter2 + '_' + 'MC'+ str(nMC) + '_omit_'+ str(indOmit))
			 
    return DirNames

    
        

def makeVectorPlot(root, DirName, magCut):  
    residuals.ResVectorPlot(root=root + DirName + '/', align='align/align_t',poly='polyfit_d/fit', useAccFits=False, magCut = magCut)



def makeResPlot(root, DirName):
#       residuals.plotStar(['ob110022', 'p001_14_1.8', 'p002_16_1.0', 's000_16_1.1', 'p003_16_2.3', 's002_17_1.5'], 
#                         rootDir=root + DirName + '/', align='align/align_t', poly='polyfit_d/fit', points='/points_d/', 
#                         radial=False, NcolMax=3, figsize=(15,15))
#     residuals.plotStar(['ob110125', 'S1_16_3.9', 'S6_17_3.8', 'S13_18_1.7', 'S14_18_2.7', 'p004_18_3.0'], 
#                        rootDir=root + DirName + '/', align='align/align_t', poly='polyfit_d/fit', points='/points_d/', 
#                        radial=False, NcolMax=3, figsize=(15,15))     
    residuals.plotStar(['ob120169_R', 'p005_15_3.5', 'S2_16_2.5', 'p000_16_3.6', 'S6_17_2.4', 'S7_17_2.3'], 
                       rootDir=root + DirName + '/', align='align/align_t', poly='polyfit_d/fit', points='/points_d/', 
                       radial=False, NcolMax=3, figsize=(15,15))                     


    
def GetVel(root, DirName):

    velX = np.genfromtxt(root + DirName + '/polyfit_d/fit.linearFormal', usecols=(2), comments=None, 
                        unpack=True, dtype=None, skip_header=1)
    velY = np.genfromtxt(root + DirName + '/polyfit_d/fit.linearFormal', 
                        usecols=(8), comments=None, 
                        unpack=True, dtype=None, skip_header=1)
    return velX, velY                    



def PlotVelSig(plotDir, velXarr, velYarr):

#     Nstars = len(velXarr[0])
    Njackknifes = len(velXarr)
    Nstars=[]
    for i in range(Njackknifes):
        Nstars.append(len(velXarr[i]))    
    
    for i in range(np.max(Nstars)):
        velXstar = []
        velYstar = []
        for j in range(Njackknifes):
            if i < Nstars[j]:
                velXstar.append(velXarr[j][i]*10.0)
                velYstar.append(velYarr[j][i]*10.0)
        
        rmsX = np.std(np.array(velXstar))
        rmsY = np.std(np.array(velYstar))
        maxX = np.max(np.array(velXstar))
        minX = np.min(np.array(velXstar))
        maxY = np.max(np.array(velYstar))
        minY = np.min(np.array(velYstar))
        medX = np.median(np.array(velXstar))
        medY = np.median(np.array(velYstar))

        py.paxes = py.subplot(1, 2, 1)
        py.xlim(0,np.max(Nstars)+1)
#        py.plot(np.zeros(len(velXstar))+(i+1), velXstar, 'k*-', markersize=3)
        py.errorbar(i+1, medX, yerr=[[medX-minX],[maxX-medX]], color='k', markersize=0)
        rwidth = 0.5
        rect = py.Rectangle((i+0.5+rwidth/2., medX-rmsX), rwidth, 2*rmsX,  ec='red', fc='red', zorder=10)
        py.gca().add_patch(rect)
        py.xlabel('Star #')
        py.ylabel('X velocity [mas/yr]')

                      
        if i < Njackknifes:
            py.plot(np.zeros(1)+(i+1), velXstar[i], 'b*',markersize=3, markeredgecolor='b',zorder=10)
		
        py.paxes = py.subplot(1, 2, 2)
        py.xlim(0,np.max(Nstars)+1)
        py.errorbar(i+1, medY, yerr=[[medY-minY],[maxY-medY]], color='k', markersize=0)
        rect = py.Rectangle((i+0.5+rwidth/2., medY-rmsY), rwidth, 2*rmsY,  ec='red', fc='red', zorder=10)
        py.gca().add_patch(rect)
#        py.plot(np.zeros(len(velYstar))+(i+1), velYstar, 'k*-')
        py.xlabel('Star #')
        py.ylabel('Y velocity [mas/yr]')
        if i < Njackknifes:
            py.plot(np.zeros(1)+(i+1), velYstar[i], 'b*',markersize=3, markeredgecolor='b',zorder=10)

    
    py.subplots_adjust(left = 0.15, wspace=0.4, hspace=0.33, right=0.9, top=0.9)
    
    py.savefig(plotDir + '/Vel_JackKnife.eps')
    py.savefig(plotDir + '/Vel_JackKnife.png')
    
    py.clf()



def GetVelSigDist(root, DirName):

    sigVelX = np.genfromtxt(root + DirName + '/polyfit_d/fit.linearFormal', usecols=(4), comments=None,
                     unpack=True, dtype=None, skip_header=1)
    sigVelY = np.genfromtxt(root + DirName + '/polyfit_d/fit.linearFormal',
                         usecols=(10), comments=None,
                         unpack=True, dtype=None, skip_header=1)
    
    Nstars = len(sigVelX)

    return sigVelX, sigVelY, Nstars



def PlotVelSigDist(plotDir, relErrX, relErrY):
    
    py.clf()
    fontsize1 = 10
    bins = np.arange(-7, 7, 1)
    print relErrX
    paxes = py.subplot(1, 2, 1)
    (n, b, p) = py.hist(relErrX, bins, color='b')
    py.axis([-5, 5, 0, 180], fontsize=10)
    py.xlabel('X Residuals (sigma)', fontsize=fontsize1)
    py.ylabel('Number of Trias', fontsize=fontsize1)
    ggx = np.arange(-7, 7, 0.25)
    ggy = py.normpdf(ggx, 0, 1)
    ggamp = ((py.sort(n))[-2:]).sum() / (2.0 * ggy.max())
    py.plot(ggx, ggy*ggamp, 'r-', linewidth=2)

    paxes = py.subplot(1, 2, 2)
    
    #             subplot(3, 2, 5)
    (n, b, p) = py.hist(relErrY, bins, color='b')
    py.axis([-5, 5, 0, 180], fontsize=10)
    py.xlabel('Y Residuals (sigma)', fontsize=fontsize1)
    py.ylabel('Number of Trials', fontsize=fontsize1)
    ggx = np.arange(-7, 7, 0.25)
    ggy = py.normpdf(ggx, 0, 1)
    ggamp = ((py.sort(n))[-2:]).sum() / (2.0 * ggy.max())
    py.plot(ggx, ggy*ggamp, 'r-', linewidth=2)
    py.savefig(plotDir + '/velDist_a3_m20_w1-4.eps')
    py.clf()
