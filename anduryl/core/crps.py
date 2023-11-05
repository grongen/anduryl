import numpy as np
import math
from scipy.special import fresnel


def _complex1_arr(k, N):
    frac = 2 * (k / N) ** 0.5
    parts = np.stack(fresnel(frac)[::-1], axis=1) / frac[:, None]
    parts[:, 1] *= -1
    z = parts.view(np.complex_)
    return z.ravel()


def _complex2_arr(k, N, x):
    z = np.zeros((len(k), len(x), 2))
    z[:, :, 1] = 2 * math.pi * k[:, None] * x[None, :] / N
    return z.view(np.complex_)


def f_N_distribution(N, x, kmax=10000):
    k = np.arange(1, kmax)

    p1 = _complex1_arr(k, N) ** N
    p2 = np.exp(_complex2_arr(k, N, x)) / k[:, None, None]

    summand_term = p1[:, None, None] * p2

    f_N = 1 / 6 + x / N + 1 / math.pi * summand_term.imag.sum(axis=0).ravel()

    return f_N


def crps_sa(quantiles, minscore=1e-20):

    N = len(quantiles)
    crps_real = quantiles**3 / 3 - (quantiles - 1) ** 3 / 3

    z_real = crps_real * 4 - 1 / 3

    # sum_z_real = np.sum(z_real)

    results = 1 - f_N_distribution(N, np.atleast_1d(z_real.sum()))

    # In case of a sum(z) very close to N, the distribution can return a value slightly larger than 1.0,
    # resulting in a score lower than 0.0. In that case, return 0.0
    return np.maximum(np.full_like(results, minscore), results)
