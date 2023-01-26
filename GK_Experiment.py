""" 
Reproduces the G-and-K distribution inference problem.
"""
from numpy.random import default_rng
from numpy import concatenate, exp, array, zeros, eye, save
from scipy.stats import multivariate_normal as MVN
from scipy.special import ndtri
from Manifolds import GKManifold
from TangentialHug import THUG
from HelperFunctions import compute_arviz_miness_runtime
import time 


def data_generator(θ0, m, seed):
    """Stochastic Simulator. Generates y given θ for the G-and-K problem."""
    rng = default_rng(seed)
    z = rng.normal(size=m)
    ξ = concatenate((θ0, z))
    return ξ[0] + ξ[1]*(1 + 0.8*(1 - exp(-ξ[2]*ξ[4:]))/(1 + exp(-ξ[2]*ξ[4:]))) * ((1 + ξ[4:]**2)**ξ[3])*ξ[4:]


def generate_setting(m, ϵs, Bs, δ, n_chains, n_samples):
    """Generates an object from which one can grab the settings. This allows one to run multiple scenarios."""
    θ0        = array([3.0, 1.0, 2.0, 0.5])      # True parameter value on U(0, 10) scale.
    d         = 4 + m                            # Dimensionality of ξ=(θ, z)
    ystar     = data_generator(θ0, m, seed=1234) # Observed data
    q         = MVN(zeros(d), eye(d))            # Proposal distribution for THUG
    manifold  = GKManifold(ystar)
    ξ0        = manifold.find_point_on_manifold_from_θ(ystar=ystar, θfixed=ndtri(θ0/10), ϵ=1e-5, maxiter=5000, tol=1e-15)
    return {
        'θ0': θ0,
        'm' : m,
        'ystar': ystar,
        'q': q,
        'ξ0': ξ0,
        'ϵs': ϵs,
        'Bs': Bs,
        'δ': δ,
        'n_chains': n_chains,
        'n_samples': n_samples,
        'manifold': manifold
    }


def compute_average_computational_cost(SETTINGS, α, method='linear'):
    """RUNS n_chains of THUG for each B and ϵ provided."""
    q = SETTINGS['q']
    ξ0, ϵs, Bs, N_samples = SETTINGS['ξ0'], SETTINGS['ϵs'], SETTINGS['Bs'], SETTINGS['n_samples']
    n_ϵ = len(ϵs)
    n_B = len(Bs)
    n_chains = SETTINGS['n_chains']
    manifold = SETTINGS['manifold']
    δ = SETTINGS['δ']
    THUG_CC = zeros((n_ϵ, n_B))
    THUG_AP = zeros((n_ϵ, n_B))
    for ϵ_ix, ϵ in enumerate(ϵs):
        for B_ix, B in enumerate(Bs):
            chains   = []
            times    = []
            avg_ap   = 0.0
            for _ in range(n_chains):
                # Store the chain and average the times and acceptance probabilities
                logηϵ = manifold.generate_logηϵ(ϵ)  
                start_time = time.time()
                samples, acceptances = THUG(x0=ξ0, T=B*δ, B=B, N=N_samples, α=α, q=q, logpi=logηϵ, jac=manifold.fullJacobian, method=method)
                runtime = time.time() - start_time
                chains.append(samples)
                times.append(runtime)
                avg_ap   += (acceptances.mean() / n_chains)
            # After having gone through each chain, compute the ESS
            THUG_CC[ϵ_ix, B_ix] = compute_arviz_miness_runtime(chains, times)
            THUG_AP[ϵ_ix, B_ix] = avg_ap
    return THUG_CC, THUG_AP


if __name__ == "__main__":
    ### Dimensionality of the data: 50
    SETTINGS_50 = generate_setting(
        m=50,
        ϵs=[1.0, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001, 0.0000001, 0.00000001],
        Bs=[1, 10, 50],
        δ=0.01,
        n_chains=4,
        n_samples=1000
    )

    ### Run Tangential Hug (α=0.0, 0.9, 0.99)
    THUG00_CC, THUG00_AP = compute_average_computational_cost(SETTINGS_50, α=0.0)
    save('GK_Experiment/THUG00_CC.npy', THUG00_CC)
    save('GK_Experiment/THUG00_AP.npy', THUG00_AP)

