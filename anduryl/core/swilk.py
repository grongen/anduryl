import numpy as np
from statistics import NormalDist
from collections import namedtuple
from scipy.stats import shapiro, beta
from numpy.core.multiarray import interp as compiled_interp

_SW_Weights = {}
_SW_ECDF = {}


def _prepare_SW_ecdf(N):
    Nsamp = int(1e6)
    x = np.sort(np.random.randn(N, Nsamp), axis=0)
    SW = np.sort(swilk_statistic_arr(x, is_sorted=True))
    ranks = (np.arange(len(SW)) + 0.5) / Nsamp

    xpts = np.linspace(SW.min(), SW.max(), 1000)
    ypts = np.linspace(0, 1, 1001)[1:-1]

    yinterp = np.interp(xpts, SW, ranks)
    xinterp = np.interp(ypts, ranks, SW)

    xtot = np.concatenate([[0.0], xpts, xinterp, [SW.max() * 2]])
    _, order = np.unique(xtot, return_index=True)
    ytot = np.concatenate([[0.0], yinterp, ypts, [1.0]])

    _SW_ECDF[N] = (xtot[order], ytot[order])


def _prepare_swilk_weights(N):

    """Initialized data"""
    sqrth = 0.70711

    a = np.zeros(N)

    # polynomial coefficients
    c1 = np.array([-2.706056, 4.434685, -2.07119, -0.147981, 0.221157, 0.0])
    c2 = np.array([-3.582633, 5.682633, -1.752461, -0.293762, 0.042981, 0.0])

    """ Parameter adjustments """

    n = N
    n2 = n // 2 if n % 2 == 0 else (n - 1) // 2

    nn2 = n // 2

    if n < 3:
        raise ValueError("Minimum number of required data points is 3.")

    if n == 3:
        a[0] = sqrth
    else:
        an25 = n + 0.25

        nd = NormalDist()
        a[:n2] = np.array([nd.inv_cdf(p=(i + 0.625) / an25) for i in range(n2)])

        summ2 = 2 * (a[:n2] ** 2).sum()
        ssumm2 = np.sqrt(summ2)

        rsn = 1 / np.sqrt(n)
        a1 = np.polyval(c1, rsn) - a[0] / ssumm2

        """ Normalize a[] """
        if n > 5:
            i1 = 3
            a2 = -a[1] / ssumm2 + np.polyval(c2, rsn)
            fac = np.sqrt((summ2 - 2 * a[0] ** 2 - 2 * a[1] ** 2) / (1 - 2 * a1**2 - 2 * a2**2))
            a[1] = a2
        else:
            # n == 4 or n == 5
            i1 = 2
            fac = np.sqrt((summ2 - 2 * a[0] ** 2) / (1 - 2 * a1**2))

        a[0] = a1
        a[i1 - 1 : nn2] /= -fac

    # Mirror array, make first part negative
    a[-n2:] = a[n2 - 1 :: -1]
    a[:n2] *= -1

    return a


def _get_p_value(stat, N):
    # _plot_ecdf(N, stat)
    pval = compiled_interp(stat, *_SW_ECDF[N])
    return pval


def _plot_ecdf(N, stat=None):
    if N not in _SW_ECDF:
        _prepare_SW_ecdf(N)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.grid()
    ax.plot(*_SW_ECDF[N], label=N)

    if stat is not None:
        ax.axvline(stat)

    ax.legend()
    plt.show()


def swilk_statistic(x, is_sorted=False):

    if not is_sorted:
        x = np.sort(x)

    N = x.shape[0]
    if N not in _SW_Weights:
        _SW_Weights[N] = _prepare_swilk_weights(N)

    a = _SW_Weights[N]

    w = ((a * x).sum() ** 2) / (x**2).sum()

    return w


def swilk_statistic_arr(x, is_sorted=False):

    if not is_sorted:
        x = np.sort(x, axis=0)

    N = x.shape[0]
    if N not in _SW_Weights:
        _SW_Weights[N] = _prepare_swilk_weights(N)

    a = _SW_Weights[N][:, None]

    w = ((a * x).sum(axis=0) ** 2) / (x**2).sum(axis=0)

    return w


def sw_sa(x):

    # Convert quantiles to normal dist
    nd = NormalDist()
    x_norm = np.array([nd.inv_cdf(ix) for ix in x])

    N = len(x_norm)
    if N not in _SW_ECDF:
        _prepare_SW_ecdf(N)

    swilk_stat = swilk_statistic(x_norm)
    return _get_p_value(swilk_stat, N)


if __name__ == "__main__":


    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    params = [(0.4, 0.4), (1, 1), (2, 2), (1, 2)]
    for a, b in params:
        dist = beta(a, b)
        sas = []
        for _ in range(1000):
            x = dist.rvs(51)
            sas.append(sw_sa(x))
        ax.hist(sas, alpha=0.3, range=(0, 1), bins=33, label='{} {}'.format(a, b))
    
    ax.legend()
    plt.show()

    

    print()

    # _x = x.copy()
    # _x -= x.mean()
    # _x /= x.std()

    # import timeit

    # start = timeit.default_timer()
    # print(timeit.default_timer() - start)

    # from scipy.stats import shapiro

    # start = timeit.default_timer()
    # print(shapiro(x))
    # print(timeit.default_timer() - start)
