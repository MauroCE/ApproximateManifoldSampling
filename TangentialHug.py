from numpy import zeros, log, vstack, zeros_like, eye
from numpy.random import default_rng, randint
from numpy.linalg import solve, norm
from scipy.linalg import qr, lstsq
from scipy.stats import multivariate_normal as MVN
from warnings import catch_warnings, filterwarnings


def THUG(x0, T, B, N, α, logpi, jac, method='qr', rng=None, safe=True):
    """Tangential Hug Sampler  (THUG). Two projection methods available:
        - 'qr': projects onto row space of Jacobian using QR decomposition.
        - 'linear': solves a linear system to project.

    Arguments:

    :param x0: Initial state of the Markov Chain. For the algorithm to work, this should be in a region of non-zero 
               density.
    :type x0: ndarray

    :param T: Total integration time. It is the product of the number of bounces and the step-size `T = B*δ`.
    :type T: float

    :param B: Number of bounces per sample/trajectory. Equivalent to the number of leapfrog steps in HMC. `δ = T/B`.
    :type B: int

    :param N: Number of samples.
    :type N: int

    :param alpha: Squeezing parameter for THUG. Must be in `[0, 1)`. The larger alpha, the more we squeeze the 
                  auxiliary velocity variable towards the tangent space.
    :type alpha: float

    :param logpi: Function computing the log-density for the target (which should be a filamentary distribution).
    :type logpi: callable

    :param jac: Function computing the Jacobian of `f` at a point.
    :type jac: callable

    :param method: Method for projecting onto the row space of the Jacobian. Two options are available
                   `'QR'` or `'linear'`.
    :type method: string

    :param rng: Random number generator for reproducibility, typically an instance of `np.random.default_rng(seed)`.
    :type rng: int

    :param safe: Whether to safely compute the Jacobian or not. If `True`, we do not allow any Runtime Warning or 
                 Overflow of any kind and raise an error. Otherwise, we let the algorithm run.
    :type safe: bool

    Returns: 

    :param samples: `(N, len(x0))` array contianing the samples from `logpi`.
    :type samples: ndarray

    :param acceptances: Array of `0`s and `1`s indicating whether a certain sample was an acceptance or rejection.
    :type acceptances: ndarray
    """
    assert method == 'qr' or method == 'linear' or method == 'lstsq' or method == '2d'
    if rng is None:
        rng = default_rng(seed=randint(low=1000, high=9999))
    def qr_project(v, J):
        """Projects using QR decomposition."""
        Q, _ = qr(J.T, mode='economic')
        return Q.dot((Q.T.dot(v)))
    def linear_project(v, J):
        """Projects by solving linear system."""
        return J.T.dot(solve(J.dot(J.T), J.dot(v)))
    def lstsq_project(v, J):
        """Projects using scipy's Least Squares Routine."""
        return J.T.dot(lstsq(J.T, v)[0])
    def project_2d(v, g):
        """Projection function for when the constraint function f:R^n -> R is scalar-valued.
        In this case, the Jacobian function is actually a vector `g`, i.e. the gradient. 
        We assume the gradient is a (2, ), i.e. a row numpy array, not a column vector (2, 1). """
        g_hat = g / norm(g)
        return g_hat * (g_hat @ v)

    if method == 'qr':
        project = qr_project
    elif method == 'linear':
        project = linear_project
    elif method == 'lstsq':
        project = lstsq_project
    else:
        project = project_2d
    # Jacobian function raising an error for RuntimeWarning
    def safe_jacobian_function(x):
        """Raises an error when a RuntimeWarning appears."""
        while catch_warnings():
            filterwarnings('error')
            try:
                return jac(x)
            except RuntimeWarning:
                raise ValueError("Jacobian computation failed due to Runtime Warning.")
    safe_jac = safe_jacobian_function if safe else jac
    samples, acceptances = x0, zeros(N)
    q = MVN(mean=zeros_like(x0), cov=eye(len(x0)))
    # Compute initial Jacobian. 
    for i in range(N):
        v0s = rng.normal(size=len(x0))
        # Squeeze
        v0 = v0s - α * project(v0s, safe_jac(x0))
        v, x = v0, x0
        logu = log(rng.uniform())
        δ = T / B
        for _ in range(B):
            x = x + δ*v/2
            v = v - 2 * project(v, safe_jac(x)) 
            x = x + δ*v/2
        # Unsqueeze
        v = v + (α / (1 - α)) * project(v, safe_jac(x)) 
        if logu <= logpi(x) + q.logpdf(v) - logpi(x0) - q.logpdf(v0s):
            samples = vstack((samples, x))
            acceptances[i] = 1         # Accepted!
            x0 = x
        else:
            samples = vstack((samples, x0))
            acceptances[i] = 0         # Rejected
    return samples[1:], acceptances
