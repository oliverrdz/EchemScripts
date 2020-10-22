#!/usr/bin/python

import numpy as np
from scipy.linalg import solve_banded

## Electrochemistry constants
F = 96485 # C/mol, Faraday constant    
R = 8.315 # J/mol K, Gas constant
T = 298 # K, Temperature
FRT = F/(R*T)

class FD:

    def __init__(self, wf, n=1, Ageo=1, cOb=1e-6, cRb=1e-6, DO=1e-5, DR=1e-5, 
                 E0=0, ks=1e5, alpha=0.5):
        E = wf.E
        t = wf.t
        
        DOR = DO/DR

        nT = np.size(t)
        dT = 1/nT
        lamb = 0.45
        #%% Simulation parameters
        nT = np.size(t) # number of time elements
        dT = 1/nT # adimensional step time
        lamb = 0.45 # For the algorithm to be stable, lamb = dT/dX^2 < 0.5
        Xmax = 6*np.sqrt(nT*lamb) # Infinite distance
        dX = np.sqrt(dT/lamb) # distance increment
        nX = int(Xmax/dX) # number of distance elements

        ## Discretisation of variables and initialisation
        CR = np.ones([nT,nX]) # Initial condition for R
        CO = np.ones([nT,nX])*cOb/cRb
        X = np.linspace(0,Xmax,nX) # Discretisation of distance
        eps = (E-E0)*n*FRT # adimensional potential waveform
        delta = np.sqrt(DR*t[-1]) # cm, diffusion layer thickness
        K0 = ks*delta/DR # Normalised standard rate constant

        #%% Simulation
        for k in range(1,nT):
            # Boundary condition, Butler-Volmer:
            #CR[k,0] = (CR[k-1,1] + dX*K0*np.exp(-alpha*eps[k]))/(
            #        1+dX*K0*(np.exp((1-alpha)*eps[k])+np.exp(-alpha*eps[k])))
            CR1kb = CR[k-1,1]
            CO1kb = CO[k-1,1]
            CR[k,0] = (CR1kb + dX*K0*np.exp(-alpha*eps[k])*(CO1kb + CR1kb/DOR))/(
                       1 + dX*K0*(np.exp((1-alpha)*eps[k]) + np.exp(-alpha*eps[k])/DOR))
            CO[k,0] = CO1kb + (CR1kb - CR[k,0])/DOR
    
            # Solving finite differences:
            for j in range(1,nX-1):
                #CR[k,j] = CR[k-1,j] + lamb*(CR[k-1,j+1] - 2*CR[k-1,j] + CR[k-1,j-1])
                CR[k,j] = CR[k-1,j] + lamb*(CR[k-1,j+1] - 2*CR[k-1,j] + CR[k-1,j-1])
                CO[k,j] = CO[k-1,j] + DOR*lamb*(CO[k-1,j+1] - 2*CO[k-1,j] + CO[k-1,j-1])

        # Denormalising:
        i = n*F*Ageo*DR*cRb*(-CR[:,2] + 4*CR[:,1] - 3*CR[:,0])/(2*dX*delta)
        cR = CR*cRb
        cO = cRb - cR
        x = X*delta

        self.E = E
        self.t = t
        self.i = i
        self.cR = cR
        self.cO = cO
        self.x = x


class BI:

    def __init__(self, wf, n=1, Ageo=1, cB=1e-6, D=1e-5, E0=0, ks=1e8, alpha=0.5):
        E = wf.E
        t = wf.t

        #%% Simulation parameters
        delta = np.sqrt(D*t[-1]) # cm, diffusion layer thickness
        maxT = 1 # Time normalised by total time
        dt = t[1] # t[1] - t[0]; t[0] = 0
        dT = dt/t[-1] # normalised time increment
        nT = np.size(t) # number of time elements

        maxX = 6*np.sqrt(maxT) # Normalised maximum distance
        dX = 2e-3 # normalised distance increment
        nX = int(maxX/dX) # number of distance elements
        X = np.linspace(0,maxX,nX) # normalised distance array

        K0 = ks*delta/D # Normalised standard rate constant
        lamb = dT/dX**2

        # Thomas coefficients
        a = -lamb
        b = 1 + 2*lamb
        g = -lamb

        C = np.ones([nT,nX]) # Initial condition for C
        V = np.zeros(nT+1)
        i = np.zeros(nT)

        # Constructing ab to use in solve_banded:
        ab = np.zeros([3,nX])
        ab[0,2:] = g
        ab[1,:] = b
        ab[2,:-2] = a
        ab[1,0] = 1
        ab[1,-1] = 1

        # Initial condition for V
        V[0] = E[0]

        #%% Simulation
        for k in range(0,nT-1):
            eps = FRT*(E[k] - E0)
    
            # Butler-Volmer:
            b0 = -(1 +dX*K0*(np.exp((1-alpha)*eps) + np.exp(-alpha*eps)))
            g0 = 1
    
            # Updating ab with the new values
            ab[0,1] = g0
            ab[1,0] = b0
    
            # Boundary conditions:
            C[k,0] = -dX*K0*np.exp(-alpha*eps)
            C[k,-1] = 1
    
            C[k+1,:] = solve_banded((1,1), ab, C[k,:])
    
            # Obtaining faradaic current and solving voltage drop
            i[k] = n*F*Ageo*D*cB*(-C[k+1,2] + 4*C[k+1,1] - 3*C[k+1,0])/(2*dX*delta)
    
        # Denormalising:
        cR = C*cB
        cO = cB - cR
        x = X*delta

        self.t = t
        self.E = E
        self.i = i
        self.cR = cR
        self.cO = cO
        self.x = x

