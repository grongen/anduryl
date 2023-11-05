import numpy as np
from pathlib import Path
import pickle


def _anderson_darling_arr(x, is_sorted=False):

    if not is_sorted:
        w = np.sort(x, axis=1)
    else:
        w = x
    N = w.shape[1]

    # TODO: adjust numpy error catching to avoid needing this below:
    minvalue = 1e-323

    logcdf = np.log(np.maximum(w, minvalue))
    logsf = np.log(np.maximum(1 - w, minvalue))

    i = np.arange(1, N + 1)[None, :]
    A2 = -N - np.sum((2 * i - 1.0) / N * (logcdf + logsf[:, ::-1]), axis=1)
    return A2


def _anderson_darling(x):

    if x.ndim > 1:
        return _anderson_darling_arr(x)

    w = np.sort(x)
    minvalue = 1e-323
    N = len(w)

    logcdf = np.log(np.maximum(w, minvalue))
    logsf = np.log(np.maximum(1 - w, minvalue))

    i = np.arange(1, N + 1)
    AD = -N - np.sum((2 * i - 1.0) / N * (logcdf + logsf[::-1]), axis=0)

    return AD


def d(a, n):
    return (
        (0.23945 * n**-0.9379 - 0.1201 * n**-0.9600 - 0.0002816) * a
        - 1.437 * n**-0.9379
        + 1.441 * n**-0.9600
        + 0.0008899
    )

def q(a):
    return a**-0.48897 * np.exp(-a - 0.06420)


def F_AD_grace(a, n):
    F = q(a) * np.exp(d(a, n))
    return F


def p1(a):
    return (
        a**-0.5
        * np.exp(-1.2337141 / a)
        * (2.00012 + (0.247105 - (0.0649821 - (0.0347962 - (0.0116720 - 0.00168691 * a) * a) * a) * a) * a)
    )


def p2(a):
    return np.exp(-np.exp(1.0776 - (2.30695 - (0.43424 - (0.082433 - (0.008056 - 0.0003146 * a) * a) * a) * a) * a))


def c(n):
    return 0.01265 + 0.1757 / n


def g1(pa):
    return pa**0.5 * (1 - pa) * (49 * pa - 102)


def g2(pa):
    # note that the (Grace, 2012) article contains a double minus which should be a minus in (8) for g2(p(a))
    return -0.00022633 + (6.54034 - (14.6538 - (14.458 - (8.259 - 1.91864 * pa) * pa) * pa) * pa) * pa


def g3(pa):
    return -130.2137 + (745.2337 - (1705.091 - (1950.646 - (1116.360 - 255.7844 * pa) * pa) * pa) * pa) * pa


def e1(n, pa, cn):
    return (0.0037 / n**3 + 0.00078 / n**2 + 0.00006 / n) * g1(pa / cn)


def e2(n, pa, cn):
    return (0.04213 / n + 0.01365 / (n**2)) * g2((pa - cn) / (0.8 - cn))


def e3(n, pa):
    return g3(pa) / n


def F_AD_MandM(a, n):
    pa = np.where(a < 2, p1(a), p2(a))
    cn = c(n)
    e_n_pa = np.where(pa < cn, e1(n, pa, cn), np.where(pa > 0.8, e3(n, pa), e2(n, pa, cn)))
    return 1 - pa - e_n_pa


def _get_p_value(AD, N):

    # For values of AD smaller than 3, use the method from (Marsaglia and Marsaglia, 2004)
    if AD < 3:
        return F_AD_MandM(AD, N)
        
    # For values of AD smaller than 3, use the method from (Grace et al., 2012)
    elif AD > 4:
        return F_AD_grace(AD, N)

    # For values in between interpolate to ensure a smooth transition
    else:
        p_a_small = F_AD_MandM(AD, N)
        p_a_large = F_AD_grace(AD, N)
        fraction = 4 - AD
        return p_a_small * fraction + p_a_large * (1 - fraction)



# def _prepare_AD_ecdf(N):
#     Nsamp = int(round(1e8 / N))

#     r = RandomState(N)
#     x = r.rand(Nsamp, N)

#     AD = np.sort(_anderson_darling_arr(x, is_sorted=False))
#     ranks = (np.arange(len(AD)) + 0.5) / Nsamp

#     xpts = np.linspace(AD.min(), AD.max(), 1000)
#     ypts = np.linspace(0, 1, 1001)[1:-1]

#     yinterp = np.interp(xpts, AD, ranks)
#     xinterp = np.interp(ypts, ranks, AD)

#     xtot = np.concatenate([[0.0], xpts, xinterp, [AD.max() * 2]])
#     _, order = np.unique(xtot, return_index=True)
#     ytot = np.concatenate([[0.0], yinterp, ypts, [1.0]])

#     _AD_ECDF[N] = (xtot[order], ytot[order])

#     _save_ECDF()
#     # _AD_ECDF[N] = (AD, ranks)


def _plot_ecdf(N):
    # if N not in _AD_ECDF:
        # _prepare_AD_ecdf(N)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    AD = np.linspace(1e-3, 20, 1001)
    # _prepare_AD_ecdf(N)

    ax.plot(_get_p_value(AD, N), label=N)

    ax.legend()
    plt.show()


def ad_sa(x):

    N = len(x)
    AD = _anderson_darling(x)
    p = _get_p_value(AD, N)
    return p


if __name__ == "__main__":

    for _ in range(20):
        x = np.sort((np.random.rand(51)))
        print(1, ad_sa(x))

    # x = np.sort(np.random.rand(101))
    # print(2, ad_sa(x))

    # x = np.random.rand(100)
    N = 10
    # Nsamp = 1000000

    # x = np.random.rand(Nsamp, N)
    # AD = anderson_darling(x)
    # print(AD.max())
    # ranks = (np.argsort(np.argsort(AD)) + 0.5) / Nsamp
    # ax.hist(AD, bins=100, alpha=0.5, range=(0, N))
    # ax.plot(AD, ranks, marker=".", ls="")

    # x -= x.mean(axis=1)[:, None]
    # x /= x.std(ddof=1, axis=1)[:, None]

    # print(anderson(x[0]).statistic)
    # print(anderson_darling(norm.cdf(x[0])))
    # print(anderson_darling_arr(norm.cdf(x)))
    # print()

    # AD = anderson_darling_arr(x)
    # ax.hist(AD, bins=100, alpha=0.5, range=(0, N))
    # plt.show()

# # FitResult initializer expects an optimize result, so let's work with it
# message = '`anderson` successfully fit the distribution to the data.'
# res = optimize.OptimizeResult(success=True, message=message)
# res.x = np.array(fit_params)
# fit_result = FitResult(getattr(distributions, dist), y,
#                        discrete=False, res=res)
