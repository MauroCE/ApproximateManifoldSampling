# Approximate Manifold Sampling
### Aim
The code in this repository is structured to minimize the reading time. I have traded-off code duplication for transparency. 

### Background
The THUG algorithm is designed to sample efficiently from probability distributions **highly concentrated around** a lower-dimensional manifold. The manifold is implicitly defined as the $0$-level set of a smooth function $f:\mathbb{R}^n\to\mathbb{R}^m$

$$ \mathcal{M} := f^{-1}(0) = \left\\{x\in\mathbb{R}^n\\,:\\, f(x) = 0\right\\} $$

The key behind its efficiency is in its nifty bounce mechanism that allows it to bounce around $\mathcal{M}$ with high precision, without the use of optimization routines.

### Visualization
Consider a mixture of two Gaussians concentrated around an ellipse. Standard sampling algorithms such as Random Walk Metropolis or Hamiltonian Monte Carlo struggle to efficiently sample from these types of distributions, but THUG is well-adapted to this task.

![Approximate Manifold Sampling](/images/rwm_vs_hug_on_ellipse_density_with_varying_stepsize.png)


### Related Projects
Exact manifold sampling has been addressed in many papers, we refer to the paper for a thorough literature review. [Mici](https://github.com/matt-graham/mici) contains code to run Constrained Hamiltonian Monte Carlo. In this repository we compare THUG with Constrained Random Walk, which is a special case of C-HMC for a constant potential. 

