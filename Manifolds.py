"""
This file contains various classes relating to Manifolds.

    - Manifold: the base class, implements an abstract manifold. Every other class inherits from it.
    - Generalized Ellipse: level set of a MVN
    - LVManifold: manifold for the Lotka-Volterra problem.
    - GKManifold: manifold for the G-and-K problem.
"""
import math
import numpy as np
from numpy import log, pi, zeros, eye, ones, exp, sqrt, diag, apply_along_axis, concatenate, vstack, isfinite, array
from numpy.random import default_rng
from numpy.linalg import svd, inv, det
from scipy.optimize import fsolve
from scipy.stats import multivariate_normal as MVN
from scipy.stats import norm as ndist
from scipy.stats import uniform as udist
from scipy.special import ndtr, ndtri
from scipy.linalg import block_diag
from warnings import catch_warnings, filterwarnings


class Manifold:
    def __init__(self, m, d):
        """
        Generic Manifold Class. This class implements an abstract "manifold". It is a simple and compact way to 
        gether together several properties and functions related to a manifold. Importantly, this class only represents
        implicitly-defined manifold, i.e. given a smooth function f:Rn -> Rm with n > m, the manifold is defined as the 0-level
        set of f. There is nothing special about the value 0, but it is convenient: given another function g, if the level set of interest
        is {x \in Rn : g(x) = y} then we simply define f(x) = g(x) - y.

        Arguments: 
        
        :param m: Number of constraints. Co-Dimension of the manifold. For instance, for a Sphere in 3D this would be 1.
        :type m: int

        :param d: Dimension of the manifold. For instance, for a Sphere in 3D this would be 2.
        :type d: int
        """
        self.m = m                # Co-Dimension of the Manifold
        self.d = d                # Dimension of the Manifold
        self.n = self.m + self.d  # Dimension of the Ambient Space

    def tangent_basis(self, Q):
        """
        Computes a tangent basis from the Q matrix (the transpose of the Jacobian matrix).

        Arguments:

        :param Q: 2D Numpy array containing gradients of the constraints as columns. It is the transpose of 
                  the Jacobian. Has dimension `(m + d, m)`.
        :type Q: ndarray

        Returns: 

        :param tangent_basis: Matrix containing basis of tangent space as its columns. 
        :type tangent_basis: ndarray
        """
        assert Q.shape == (self.m + self.d, self.m), "Q must have shape ({}, {}) but found shape {}".format(self.m+self.d, self.m, Q.shape)
        return svd(Q)[0][:, self.m:]

    def get_dimension(self):
        """
        Returns dimension of the manifold d.
        """
        return self.d
    
    def get_codimension(self):
        """
        Returns co-dimension of the manifold d.
        """
        return self.m


class GeneralizedEllipse(Manifold):
    def __init__(self, mu, Sigma, z):
        """
        Class implementing the ellipsoid corresponding to the `z`-level set of a 
        multivariate normal (MVN) with mean `mu` and covariance matrix `Sigma`.

        Arguments: 

        :param mu: Center of the Ellipsoid, or equivalently, mean of the MVN. Must be a 1D array of dimension (3, ).
        :type mu: ndarray

        :param Sigma: Covariance matrix of the MVN, specifying angle and scaling of ellipse. Must be a 3x3 matrix.
        :type Sigma: ndarray

        :param z: Level-set value. This identifies which level-set/contour of the MVN to consider.
        :type z: float
        """
        self.n = len(mu)    # Dimension of the ambient space
        # Store MVN parameters
        self.z = z
        self.mu = mu
        self.S = Sigma
        self.Sinv = inv(Sigma)
        self.mu = mu
        self.logdetS = log(det(self.S))
        self.MVN = MVN(self.mu, self.S)
        # Compute gamma (RHS) 
        self.gamma = -self.n * log(2*pi) - self.logdetS -2 * log(z)
        super().__init__(m=1, d=(self.n-1))

    def q(self, xyz):
        """Constraint function for the contour of MVN.
        
        Arguments: 

        :param xyz: Input array at which we want to evaluate the constraint. Must have shape (3, ).
        :type xyz: ndarray

        Returns: 

        :param q_xyz: Value of the constraint function at `xyz`.
        :type q_xyz: ndarray
        """
        return (xyz - self.mu) @ (self.Sinv @ (xyz - self.mu)) - self.gamma

    def Q(self, xyz):
        """Transpose of the Jacobian matrix of the constraint function. Notice that for our experiments we will
        not actually use this but use `fullJacobian` due to reparametrization issues.
        
        Arguments: 

        :param xyz: Input array at which we want to evaluate the constraint. Must have shape (3, ).
        :type xyz: ndarray

        Returns: 

        :param Q_xyz: Transpose of the Jacobian (unparametrized) evaluated at `xyz`.
        :type Q_xyz: ndarray
        """
        return (2 * self.Sinv @ (xyz - self.mu)).reshape(-1, self.m)

    def sample(self):
        """Samples from the contour by first sampling a point from the original
        MVN and then it rescales it until it is on the correct contour. This should
        work since the MVN is spherically symmetric."""
        start = self.MVN.rvs()   # Get initial MVN sample
        objective = lambda coef: self.MVN.pdf(coef*start) - self.z  # Objective function checks closeness to z
        optimal_coef = fsolve(objective, 1.0) # Find coefficient so that optimal_coef*start is on contour
        return start * optimal_coef
    

class BIPManifold(Manifold):
    def __init__(self, ??, ystar):
        """Manifold for the Bayesian Inverse Problem."""
        self.m = 1                 # One constraint F(theta, eta) = y
        self.d = 2                 # Dimension on manifold is 3 - 1 = 2.
        self.n = self.m + self.d   # Dimension of ambient space
        self.?? = ??                 # Noise scale
        self.ystar = ystar         # Observed data

    def q(self, ??):
        """Constraint for toy BIP experiment."""
        return array([??[1]**2 + 3 * ??[0]**2 * (??[0]**2 - 1)]) + self.??*??[2] - self.ystar

    def Q(self, ??):
        """Transpose of Jacobian for toy BIP. This is for the lifted manifold. Should not be used for THUG."""
        return array([12*??[0]**3 - 6*??[0], 2*??[1], self.??]).reshape(-1, self.m)

    def J(self, ??):
        """Jacobian for the toy BIP. This is for the lifted manifold. Should not be used for THUG."""
        return array([12*??[0]**3 - 6*??[0], 2*??[1], self.??]).reshape(self.m, -1)

    def log??(self, ??):
        """log posterior for c-rwm"""
        J = self.J(??)
        return - ??[:2]@??[:2]/2 - ??[-1]**2/2 - log(J@J.T + self.??**2)[0, 0]/2



class LVManifold(Manifold):
    def __init__(self, Ns=50, step_size=1.0, ??r=1.0, ??f=1.0, r0=100, f0=100, z_true=(0.4, 0.005, 0.05, 0.001), seed=1111, seeds=[2222, 3333, 4444, 5555], n_chains=4):
        """Class defining the data manifold for the Lotka-Volterra ABC problem. The simulator is defined by an
        Euler-Marayama discretization of the LV SDE.

        Arguments: 

        :param Ns: Number of discretization time steps used in the forward simulator. Defaults to `50`.
        :type Ns: int 

        :param step_size: Step size used in the discretization in the forward simulator. Default to `1.0`.
        :type step_size: float

        :param r0: Number of preys at time `t=0`. Initial condition of the SDE. Defaults to `100`.
        :type r0: int

        :param f0: Number of predators at time `t=0`. Initial condition of the SDE. Defaults to `100`.
        :type f0: int

        :param z_true: True parameter values used to generate the data. Defaults to `(0.4, 0.005, 0.05, 0.001)`.
        :type z_true: tuple

        :param seed: Random seed used to generate the data `y^*`. Defaults to `1111`.
        :type seed: int

        :param seeds: List of random seeds. Each seed is used to find the initial point for each chain. 
                      Defaults to `[2222, 3333, 4444, 5555]`.
        :type seeds: list

        :param n_chains: Number of chains used to compute ESS using Arviz. Defaults to `4`.
        :type n_chains: int
        """
        assert len(seeds) == n_chains, "Number of seeds must equal number of chains."
        self.Ns = Ns              # Number of steps used in integrating LV SDE
        self.m = 2*self.Ns        # Number of constraints = dimensionality of data
        self.d = 4                # Dimensionality of parameter
        self.n = self.d + self.m  # Dimensionality of ambient space
        self.?? = step_size        # Step size for discretization (not for sampling!)
        self.??r = ??r              # Scale for noise in prey step
        self.??f = ??f              # Scale for noise in predator step
        self.r0 = r0              # Initial prey population
        self.f0 = f0              # Initial predator population
        self.z_true = np.array(z_true)  # True parameter
        self.q_dist = MVN(zeros(self.n), eye(self.n))   # proposal for THUG
        self.seeds = seeds
        self.rngs = [default_rng(seed) for seed in self.seeds]
        self.n_chains = n_chains 
        
        # generate data
        self.data_seed = seed
        self.rng = default_rng(self.data_seed)
        self.u1_true = self.z_to_u1(self.z_true)
        self.u2_true = self.rng.normal(loc=0.0, scale=1.0, size=2*self.Ns)
        self.u_true = np.concatenate((self.u1_true, self.u2_true))
        self.ystar  = self.u_to_x(self.u_true)
        
    def z_to_u1(self, z):
        """Transforms a parameter `z` into `u1` (standard normal variables)."""
        assert len(z) == 4, "z should have length 4, but found {}".format(len(z))
        m_param = -2*ones(4)
        s_param = ones(4)
        return (log(z) - m_param) / s_param
    
    def u1_to_z(self, u1):
        """Given `u1`, it maps it to `z`."""
        assert len(u1) == 4, "u1 should have length 4, but found {}".format(len(u1))
        m_param = -2*ones(4)
        s_param = ones(4)
        return exp(s_param*u1 + m_param)
    
    def g(self, u):
        """Takes `[u1, u2]` and returns `[z, u2]`"""
        assert len(u) == self.n, "u should have length {}, but found {}".format(self.n, len(u))
        return np.concatenate((self.u1_to_z(u[:4]), u[4:]))
    
    def u_to_x(self, u):
        """Maps `u=[u1, u2]` to `z`."""
        assert len(u) == self.n, "u should have length {}, but found {}.".format(self.n, len(u))
        u1, u2 = u[:4], u[4:]
        u2_r   = u2[::2]
        u2_f   = u2[1::2]
        z1, z2, z3, z4 = self.u1_to_z(u1)
        r = np.full(self.Ns + 1, fill_value=np.nan)
        f = np.full(self.Ns + 1, fill_value=np.nan)
        r[0] = self.r0
        f[0] = self.f0
        for s in range(1, self.Ns+1):
            r[s] = r[s-1] + self.??*(z1*r[s-1] - z2*r[s-1]*f[s-1]) + sqrt(self.??)*self.??r*u2_r[s-1]
            f[s] = f[s-1] + self.??*(z4*r[s-1]*f[s-1] - z3*f[s-1]) + sqrt(self.??)*self.??f*u2_f[s-1]
        return np.ravel([r[1:], f[1:]], 'F')
    
    def zu2_to_x(self, zu2):
        """Same as `u_to_x` but this takes as input `[z, u2]`."""
        assert len(zu2) == self.n, "zu2 should have length {}, but found {}".format(self.n, len(zu2))
        z1, z2, z3, z4 = zu2[:4]
        u2 = zu2[4:]
        u2_r = u2[::2]
        u2_f = u2[1::2]
        r = np.full(self.Ns + 1, fill_value=np.nan)
        f = np.full(self.Ns + 1, fill_value=np.nan)
        r[0] = self.r0
        f[0] = self.f0
        for s in range(1, self.Ns+1):
            r[s] = r[s-1] + self.??*(z1*r[s-1] - z2*r[s-1]*f[s-1]) + sqrt(self.??)*self.??r*u2_r[s-1]
            f[s] = f[s-1] + self.??*(z4*r[s-1]*f[s-1] - z3*f[s-1]) + sqrt(self.??)*self.??f*u2_f[s-1]
        return np.ravel([r[1:], f[1:]], 'F')
    
    def Jg(self, ??):
        """Jacobian of the function `g:[u_1, u_2] --> [z, u_2]`."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        m_param = -2*ones(4)
        s_param = ones(4)
        return diag(np.concatenate((s_param*exp(s_param*??[:4] + m_param), ones(2*self.Ns))))
    
    def oneat(self, ix, length=None):
        """Generates a vector of zeros of length `length` with a one at index `ix`."""
        assert type(ix) == int, "index for oneat() should be integer but found {}".format(type(ix))
        if length is None:
            length = self.n
        output = zeros(length)
        output[ix] = 1
        return output
    
    def Jf(self, ??):
        """Jacobian of the function `f:[z, u_2] --> x`.
        Assume `r` and `f` contains `r0` and `f0` at the start."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        J = zeros((self.m, self.n))
        ??  = self.??
        r0 = self.r0
        f0 = self.f0 
        ??r = self.??r
        ??f = self.??f
        # Sete first two rows: dr1_d?? and df1_d??
        J[0, :] = np.concatenate(([??*r0, -??*r0*f0, 0, 0], sqrt(??)*??r*self.oneat(0, length=self.m)))
        J[1, :] = np.concatenate(([0, 0, -??*f0, ??*r0*f0], sqrt(??)*??f*self.oneat(1, length=self.m)))
        # Evaluate function at the ?? to find r and f at this ??.
        x = self.zu2_to_x(??)
        r = np.concatenate(([r0], x[::2]))
        f = np.concatenate(([f0], x[1::2]))
        # Grab the parameters
        z1, z2, z3, z4 = ??[:4]
        # Loops through the time steps and compute the Markovian rows
        for s in range(1, self.Ns):
            J[2*s, :]     = J[2*s-2, :] + ??*(self.oneat(0)*r[s] + z1*J[2*s-2, :] -(self.oneat(1)*r[s]*f[s] + z2*J[2*s-2, :]*f[s] + z2*r[s]*J[2*s-1, :])) + sqrt(??)*??r*self.oneat(2*s+4)
            J[2*s + 1, :] = J[2*s-1, :] + ??*(self.oneat(3)*r[s]*f[s] + z4*J[2*s-2, :]*f[s] + z4*r[s]*J[2*s-1, :] - self.oneat(2)*f[s] - z3*J[2*s-1, :]) + sqrt(??)*??f*self.oneat(2*s+5)
        return J

    def q(self, ??):
        """Constraint function taking `u=[u1, u2]` and comparing against true data."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        return self.u_to_x(??) - self.ystar
    
    def J(self, ??):
        """Jacobian. Here `u=[u1, u2]`."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        return self.Jf(self.g(??)).dot(self.Jg(??))
    
    def Q(self, ??):
        """Transpose of Jacobian."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        return self.J(??).T
    
    def log??(self, ??):
        """Density on Manifold wrt Hausdorff measure."""
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        try:
            J = self.J(??)
            logprior = -??@??/2
            correction_term  = - math.prod(np.linalg.slogdet(J@J.T))/2 
            return  logprior + correction_term
        except ValueError as e:
            return -np.inf
        
    def find_point_on_manifold(self, maxiter=2000, tol=1e-14, random_u2_guess=False, rng=None):
        """Finds a point on the Manifold with input u=[u1, u2].
        
        Arguments: 
        
        :param maxiter: Maximum number of iterations allowed to find a point on the manifold before raising
                        an error.
        :type maxiter: int
        
        :param tol: Tolerance used to check for convergence withing `scipy.optimize.fsolve`.
        :type tol: float

        :param random_u2_guess: Boolean flag determining whether `u2` should be initialized at random (`True`)
                                or as a zero vector (`False`).
        :type random_u2_guess: bool

        Returns:

        :param point: Point on the manifold within tolerance `tol`. If not found, raises `ValueError`.
        :type point: ndarray
        """
        if rng is None:
            rng = default_rng(seed=np.random.randint(low=1000, high=9999))
        u2_guess = rng.normal(size=self.m) if random_u2_guess else zeros(self.m)
        i = 0
        with catch_warnings():
            filterwarnings('error')
            while i <= maxiter:
                i += 1
                try: 
                    u1_init  = rng.normal(size=self.d)*0.1 - 4 #randn(self.d)*0.1 - 4
                    function = lambda u2: self.q(np.concatenate((u1_init, u2)))
                    fprime   = lambda u2: self.J(np.concatenate((u1_init, u2)))[:, self.d:]
                    u2_found = fsolve(function, u2_guess, xtol=tol, fprime=fprime)
                    u_found = np.concatenate((u1_init, u2_found))
                    return u_found
                except RuntimeWarning:
                    continue
        raise ValueError("Couldn't find a point, try again.")
        
    def find_point_on_manifold_given_u1true(self, maxiter=2000, tol=1e-14, random_u2_guess=False, rng=None):
        """Finds a point on the Manifold starting from u1_true."""
        if rng is None:
            rng = default_rng(seed=np.random.randint(low=1000, high=9999))
        i = 0
        with catch_warnings():
            filterwarnings('error')
            while i <= maxiter:
                i += 1
                try:
                    u2_guess = rng.normal(size=self.m) if random_u2_guess else zeros(self.m)
                    function = lambda u2: self.q(np.concatenate((self.u1_true, u2)))
                    u2_found = fsolve(function, u2_guess, xtol=tol)
                    u_found = np.concatenate((self.u1_true, u2_found))
                    return u_found
                except RuntimeWarning:
                    continue
        raise ValueError("Couldn't find a point, try again.")

    def find_init_points_for_each_chain(self, u1_true=True, random_u2_guess=False, tol=1e-14, maxiter=5000):
        """Finds `n_chains` initial points on the manifold.

        Args:
            u1_true (boool, optional): Whether to use u1 that generated the data or sample it at random.
            random_u2_guess (bool, optional): Whether to generate the initial u2 guess at random or as a zero vector. Defaults to False.
            tol (float, optional): tolerance for fsolve. Defaults to 1e-14.
            maxiter (int, optional): Maximum number of iterations for optimization procedure. Defaults to 5000.

        Returns:
            ndarray: array having dimension (n_chains, n), containing each point on a row.
        """
        u0s = zeros((self.n_chains, self.n))
        for i in range(self.n_chains):
            if u1_true:
                u0s[i, :] = self.find_point_on_manifold_given_u1true(maxiter=maxiter, tol=tol, random_u2_guess=random_u2_guess, rng=self.rngs[i])
            else:
                u0s[i, :] = self.find_point_on_manifold(maxiter=maxiter, tol=tol, random_u2_guess=random_u2_guess, rng=self.rngs[i])
        self.u0s = u0s 
        return self.u0s
            
    def transform_usamples_to_zsamples(self, samples):
        """Given samples of size `(N, 4 + 2*Ns)` it takes the first 4 columns and transforms them."""
        n_samples, input_dim = samples.shape
        assert input_dim == self.n, "Wrong dim. Expected {} , found {}".format(self.n, input_dim)
        return apply_along_axis(self.u1_to_z, 1, samples[:, :4])
    
    def log_normal_kernel(self, ??, ??):
        """Log normal kernel density. Approximation to the identity.
        
        Arguments:
        
        :param xi: Point in the ambient space at which we want to evaluate the kernel.
        :type xi: ndarray
        
        :param epsilon: Bandwidth parameter for the kernel/approximation to the identity.
        :type epsilon: float
        
        Returns: 
        :param kernel_value: Kernel with bandwidth `epsilon` evaluated at `xi`.
        :type kernel_value: float
        """
        assert len(??) == self.n, "?? should have length {}, but found {}.".format(self.n, len(??))
        u = self.q(??)
        m = len(u)
        return -u@u/(2*(??**2)) - m*log(??) - m*log(2*pi)/2

    def generate_logpi(self, ??):
        """Generates ABC posterior using a certain epsilon value. Uses a Gaussian kernel. 
        
        Arguments: 
        
        :param epsilon: Epsilon used in the smoothing kernel to identify how tight the filamentary distribution is.
        :type epsilon: float

        Returns:

        :param log_eta_epsilon: Log ABC posterior with bandwidth parameter `epsilon`.
        :type log_eta_epsilon: callable    
        """
        log???? = lambda ??: self.log_normal_kernel(??, ??) - ??@??/2
        return log????
    
    def is_on_manifold(self, ??, tol=1e-14):
        """Checks if a point is on the manifold.
        
        Arguments: 
        
        :param xi: Point for which we want to check if it lies on the manifold or not.
        :type xi: ndarray

        :param tol: Tolerance used to check if `xi` is on the manifold. Defaults to `1e-14`.
        :type tol: float

        Returns 

        :param on_manifold: Boolean flag indicating if point is on manifold (`True`) or not (`False`) according
                            to tolerance `tol`.
        :type on_manifold: bool
        """
        return max(abs(self.q(??))) <= tol



    def generate_log????(self, ??, kernel='normal'):
        """Returns the log abc posterior for THUG."""
        if kernel not in ['normal']:
            raise NotImplementedError
        else:
            def log_abc_posterior(??):
                """Log-ABC-posterior."""
                u = self.q(??)
                m = len(u)
                return self.logprior(??) - u@u/(2*??**2) - m*log(??) - m*log(2*pi)/2
            return log_abc_posterior


class GKManifold(Manifold):
    def __init__(self, ystar):
        """Manifold for the G-and-K experiment. It uses the reparametrization discussed in the paper.
        
        Arguments:

        :param ystar: Observed data identifying the manifold. Must have shape (m, ).
        :type ystar: ndarray
        """
        self.m = len(ystar)            # Number constraints = dimensionality of the data
        self.d = 4                     # Manifold has dimension 4 (like the parameter ??)
        self.n = self.d + self.m       # Dimension of ambient space is m + 4
        self.ystar = ystar
        # N(0, 1) ---> U(0, 10).
        self.G    = lambda ??: 10*ndtr(??)
        # U(0, 10) ---> N(0, 1)
        self.Ginv = lambda ??: ndtri(??/10)

    def q(self, ??):
        """Constraint for G and K. This is the reparametrized constraint.
        
        Arguments: 
        
        :param xi: Point in the ambient space at which we evaluate the reparametrized constraint function.
        :type xi: ndarray
        
        Returns: 
        
        :param q_xi: Value of the constraint function at `xi`.
        :type q_xi: float
        """
        ?? = concatenate((self.G(??[:4]), ??[4:]))  # expecting theta part to be N(0, 1)
        with catch_warnings():
            filterwarnings('error')
            try:
                return (??[0] + ??[1]*(1 + 0.8*(1 - exp(-??[2]*??[4:]))/(1 + exp(-??[2]*??[4:]))) * ((1 + ??[4:]**2)**??[3])*??[4:]) - self.ystar
            except RuntimeWarning:
                raise ValueError("Constraint found Overflow warning.")
                
    def _q_raw_uniform(self, ??):
        """Constraint function expecting `??[:4] ~ U(0, 10)`. It doesn't do any warning check. 
        This is basically the original constraint function before reparametrization."""
        return (??[0] + ??[1]*(1 + 0.8*(1 - exp(-??[2]*??[4:]))/(1 + exp(-??[2]*??[4:]))) * ((1 + ??[4:]**2)**??[3])*??[4:]) - self.ystar

    def _q_raw_normal(self, ??):
        """Same as `_q_raw_uniform` except expects `??[:4]~N(0,1)`."""
        ?? = concatenate((self.G(??[:4]), ??[4:])) 
        return self._q_raw_uniform(??)

    def Qf(self, ??):
        """Transpose of Jacobian of f in the G and K problem.
        This is NOT the full Jacobian and corresponds to Jf.T. It it not the full Jacobian because we 
        are using a reparametrization. It lacks the Jacobian `JG`."""
        ?? = concatenate((self.G(??[:4]), ??[4:]))
        return vstack((
        ones(len(??[4:])),
        (1 + 0.8 * (1 - exp(-??[2] * ??[4:])) / (1 + exp(-??[2] * ??[4:]))) * ((1 + ??[4:]**2)**??[3]) * ??[4:],
        8 * ??[1] * (??[4:]**2) * ((1 + ??[4:]**2)**??[3]) * exp(??[2]*??[4:]) / (5 * (1 + exp(??[2]*??[4:]))**2),
        ??[1]*??[4:]*((1+??[4:]**2)**??[3])*(1 + 9*exp(??[2]*??[4:]))*log(1 + ??[4:]**2) / (5*(1 + exp(??[2]*??[4:]))),
        diag(??[1]*((1+??[4:]**2)**(??[3]-1))*(((18*??[3] + 9)*(??[4:]**2) + 9)*exp(2*??[2]*??[4:]) + (8*??[2]*??[4:]**3 + (20*??[3] + 10)*??[4:]**2 + 8*??[2]*??[4:] + 10)*exp(??[2]*??[4:]) + (2*??[3] + 1)*??[4:]**2 + 1) / (5*(1 + exp(??[2]*??[4:]))**2))
    ))
    
    def Jf(self, ??):
        """Computes the Jacobian J_f safely. Notice, this is not the full Jacobian, since we are using 
        a reparametrization. The full Jacobian is Jf@JGbar. 
        This is the Jacobian of which `Q` is transpose of. Again, lacks `JG`."""
        with catch_warnings():
            filterwarnings('error')
            try:
                return self.Qf(??).T
            except RuntimeWarning:
                raise ValueError("J computation found Runtime warning.")
                
    def J(self, ??):
        """J_f(G(??)) * J_G(??). This is the true Jacobian of the reparametrized constraint function.
        Obtained using the Chain Rule. This is what should be used in THUG and C-RWM algorithms."""
        JGbar = block_diag(10*np.diag(ndist.pdf(??[:4])), eye(len(??[4:])))
        return self.Jf(??) @ JGbar
                
    def log_parameter_prior(self, ??):
        """IMPORTANT: Typically the prior distribution is a U(0, 10) for all four parameters.
        We keep the same prior but since we don't want to work on a constrained space, we 
        reparametrize the problem to an unconstrained space N(0, 1).
        
        Arguments: 
        
        :param theta: Parameter at which we want to evaluate the log-prior. This should be drawn from a normal
                      distribution. The log-prior here is `U(0, 10)` so we first transform `theta` into a sample 
                      from `U(0, 10)` and then we compute the log prior. Should have length `4`.
        :type theta: ndarray

        Returns: 

        :param log_prior: Value of reparametrized log prior at `theta`. If overflow happens it returns `-np.inf`.
        :type log_prior: float
        """
        with catch_warnings():
            filterwarnings('error')
            try:
                return udist.logpdf(self.G(??), loc=0.0, scale=10.0).sum() + ndist.logpdf(??).sum()
            except RuntimeWarning:
                return -np.inf
            
    def logprior(self, ??):
        """Computes the prior distribution for G and K problem. Notice this is already reparametrized."""
        return self.log_parameter_prior(??[:4]) - ??[4:]@??[4:]/2

    def log??(self, ??):
        """Log-posterior for C-RWM. This is on the manifold."""
        try:
            J = self.J(??)
            logprior = self.logprior(??)
            correction_term  = - math.prod(np.linalg.slogdet(J@J.T))/2 
            return  logprior + correction_term
        except ValueError as e:
            return -np.inf
        
    def generate_log????(self, ??, kernel='normal'):
        """Returns the log abc posterior for THUG."""
        if kernel not in ['normal']:
            raise NotImplementedError
        else:
            def log_abc_posterior(??):
                """Log-ABC-posterior."""
                u = self.q(??)
                m = len(u)
                return self.logprior(??) - u@u/(2*??**2) - m*log(??) - m*log(2*pi)/2
            return log_abc_posterior
            
    def logp(self, v):
        """Log density for normal on the tangent space."""
        return MVN(mean=zeros(self.d), cov=eye(self.d)).logpdf(v)
    
    def is_on_manifold(self, ??, tol=1e-8):
        """Checks if ?? is on the ystar manifold."""
        return np.max(abs(self.q(??))) < tol
    
    def find_point_on_manifold_from_??(self, ??fixed, ??, maxiter=2000, tol=1.49012e-08, rng=None):
        """Finds a point on the manifold for a fixed value of `theta`. Can be used to find a point where
        the theta is already `??0`.
        
        Arguments: 
        
        :param thetafixed: Theta that we want fixed and from which we should find the latent variables such that
                           together `(theta, latent_variables)` lie on the manifold. Should have shape `(4, )`.
        :type thetafixed: ndarray

        :param epsilon: Epsilon determines a filamentary distribution. This filamentary distribution is used
                        to determine whether to accept or reject the point found via `fsolve.` Basically, this is to 
                        make sure the point still has positive mass according to a given `epsilon`-filamentary 
                        distribution. Of course, if the point is close enough to the manifold for a tolerance < `epsilon`
                        this should always be the case, but you know how programming is.
        :type epsilon: float

        :param maxiter: Maximum number of iterations used to find a point on the manifold.
        :type maxiter: int

        :param tol: Tolerance for `fsolve`. Used to find point on the manifold.
        :type tol: float

        :param rng: Random Number Generator used to start the optimization. Typically it is an instance of 
                    `np.random.default_rng(seed)` for some integer `seed`.
        :type rng: np.random.Generator
        
        Returns:
        
        :param point: Point on the manifold with theta fixed to `thetafixed`. Raises a `ValueError` if a point 
                      could not be found. 
        :type point: float
        """
        i = 0
        log_abc_posterior = self.generate_log????(??)
        function = lambda z: self._q_raw_normal(concatenate((??fixed, z)))
        # Generate a default RNG if none is provided
        if rng is None:
            rng = default_rng(seed=np.random.randint(low=1000, high=9999))
        with catch_warnings():
            filterwarnings('error')
            while i <= maxiter:
                i += 1
                try:
                    z_guess  = rng.normal(size=self.m) #randn(self.m)
                    z_found  = fsolve(function, z_guess, xtol=tol)
                    ??_found  = concatenate((??fixed, z_found))
                    if not isfinite([log_abc_posterior(??_found)]):
                        raise ValueError("Couldn't find a point.")
                    else:
                        return ??_found
                except RuntimeWarning:
                    continue
            raise ValueError("Couldn't find a point, try again.")

        
    def find_points_on_manifold_from_??(self, ??fixed, ??, rngs, maxiter=2000, tol=1.49012e-08):
        """Generates initial points according to `self.find_point_on_manifold_from_??` for each chain using
        the seeds provided (one seed per chain). This allows us to have different starting points for each 
        chain, while keeping everything reproducible.

        Arguments:
        
        :param thetafixed: Fixed theta value used to find the initial point on the manifold. This will typically
                           be the true value of theta.
        :type thetafixed: ndarray

        :param epsilon: Same as in `self.find_point_on_manifold_from_??`.
        :type epsilon: float

        :param rngs: List of RNGs for different chains. There must be one RNG per chain.
        :type rngs: np.random.Generator

        :param maxiter: Same as in `self.find_point_on_manifold_from_??`.
        :type maxiter: int

        :param tol: Same as in `self.find_point_on_manifold_from_??`.
        :type tol: float

        Returns:

        :param points: Numpy array of points on the manifold, one per chain. Each row is a point.
        :type points: ndarray
        """
        points = []
        for rng in rngs:
            point = self.find_point_on_manifold_from_??(??fixed, ??, maxiter=maxiter, tol=tol, rng=rng)
            points.append(point)
        return vstack(points)