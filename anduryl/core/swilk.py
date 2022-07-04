import numpy as np
from statistics import NormalDist
from collections import namedtuple

"""
##############################################################################
# File: ms_shapiro_wilk.cpp                                                  #
# Mascot Parser toolkit                                                      #
# Source file for Shapiro-Wilk W test                                        #
##############################################################################
#    $Source$
#    $Author$ 
#      $Date$ 
#  $Revision$
##############################################################################
"""
"""
##############################################################################
# Applied Statistics algorithms                                              #
#                                                                            #
# Translated and adapted from routines that originally appeared in the       #
# Journal of the Royal Statistical Society Series C (Applied Statistics)     #
# and made available through StatLib http://lib.stat.cmu.edu/                #
#                                                                            #
# The implementation and source code for this algorithm is available as a    #
# free download from http://www.matrixscience.com/msparser.html              #
# to conform with the requirement that no fee is charged for their use       #
##############################################################################
"""

ShapiroResult = namedtuple("ShapiroResult", ("statistic", "pvalue"))


def swilk(x, a=None, init=False):

    if a is None:
        a = np.ones_like(x) / len(x)

    w = 0  # // stop the behaviour change 'feature'
    pw = 0
    ifault = 0

    """ Initialized data """
    z90 = 1.2816
    z95 = 1.6449
    z99 = 2.3263
    zm = 1.7509
    zss = 0.56268
    bf1 = 0.8378
    xx90 = 0.556
    xx95 = 0.622
    sqrth = 0.70711
    small_value = 1e-19
    pi6 = 1.909859
    stqr = 1.047198

    # polynomial coefficients
    g = np.array([0.459, -2.273])
    c1 = np.array([-2.706056, 4.434685, -2.07119, -0.147981, 0.221157, 0.0])
    c2 = np.array([-3.582633, 5.682633, -1.752461, -0.293762, 0.042981, 0.0])
    c3 = np.array([-0.0006714, 0.025054, -0.39978, 0.544])
    c4 = np.array([-0.0020322, 0.062767, -0.77857, 1.3822])
    c5 = np.array([0.0038915, -0.083751, -0.31082, -1.5861])
    c6 = np.array([0.0030302, -0.082676, -0.4803])
    c7 = np.array([0.533, 0.164])
    c8 = np.array([0.315, 0.1736])
    c9 = np.array([-0.00635, 0.256])

    """ System generated locals """
    #     double r__1

    #     a.resize(n, 0.0)

    """
     * Auxiliary routines : np.polyval()  {below
"""

    """ Local variables """
    #     int i, j, ncens, i1, nn2

    #     double zbar, ssassx, summ2, ssumm2, gamma, delta, range
    #     double a1, a2, an, bf, ld, m, s, sa, xi, sx, xx, y, w1
    #     double fac, asa, an25, ssa, z90f, sax, zfm, z95f, zsd, z99f, rsn, ssx, xsx

    """ Parameter adjustments """

    n = len(x)
    n1 = len(x)
    n2 = n // 2 if n % 2 == 0 else (n - 1) // 2

    pw = 1.0
    ifault = 0
    if w >= 0.0:
        w = 1.0

    an = float(n)
    nn2 = n // 2
    if n2 < nn2:
        raise ValueError(f"n2 < nn2 : {n2} / {nn2}")

    if n < 3:
        raise ValueError("Minimum number of required data points is 3.")

    """  If INIT is False, calculate coefficients a[] for the test """
    if not init:
        if n == 3:
            a[0] = sqrth
        else:
            an25 = an + 0.25
            summ2 = 0.0
            nd = NormalDist()
            for i in range(1, n2 + 1, 1):
                # for (i = 1 i <= n2 ++i) :
                a[i - 1] = nd.inv_cdf(p=(i - 0.375) / an25)
                if ifault:
                    ifault = 8
                    return

                summ2 += a[i - 1] ** 2

            summ2 *= 2
            ssumm2 = np.sqrt(summ2)
            rsn = 1 / np.sqrt(an)
            a1 = np.polyval(c1, rsn) - a[0] / ssumm2

            """ Normalize a[] """
            if n > 5:
                i1 = 3
                a2 = -a[1] / ssumm2 + np.polyval(c2, rsn)
                fac = np.sqrt((summ2 - 2 * a[0] ** 2 - 2 * a[1] ** 2) / (1 - 2 * a1 ** 2 - 2 * a2 ** 2))
                a[1] = a2
            else:
                i1 = 2
                fac = np.sqrt((summ2 - 2 * a[0] ** 2) / (1 - 2 * a1 ** 2))

            a[0] = a1
            a[i1 - 1 : nn2] /= -fac

        init = True

    if n1 < 3:
        ifault = 1
        return w, pw, ifault

    ncens = n - n1
    if ncens < 0 | ((ncens > 0) & (n < 20)):
        ifault = 4
        return w, pw, ifault

    delta = ncens / an
    if delta > 0.8:
        ifault = 5
        return w, pw, ifault

    """  If W input as negative, calculate significance level of -W """
    if w < 0.0:
        w1 = 1.0 + w
        ifault = 0

    else:
        #   goto L70

        """Check for 0.0 range"""
        vrange = x[n1 - 1] - x[0]
        if vrange < small_value:
            ifault = 6
            return w, pw, ifault

        """  Check for correct sort order on range - scaled X """

        """ *ifault = 7 <-- a no-op, since it is set 0, below, in ANY CASE! """
        ifault = 0
        xx = x[0] / vrange
        sx = xx
        sa = -a[0]

        asigned = np.zeros_like(a)
        asigned[0] = -a[0]

        j = n - 1
        for i in range(2, n1 + 1, 1):
            xi = x[i - 1] / vrange
            if xx - xi > small_value:
                """Fortran had:  print *, "ANYTHING"
                * but do NOT it *does* happen with sorted x (on Intel GNU/linux):
                *  shapiro.test(c(-1.7, -1,-1,-.73,-.61,-.5,-.24, .45,.62,.81,1))
                """
                raise ValueError("Data are not in ascending order.")

            sx += xi
            if i != j:
                asigned[i - 1] = np.sign(i - j) * a[min(i, j) - 1]
                sa += asigned[i - 1]

            # print(sa)
            xx = xi
            j -= 1

        if n > 5000:
            print("Warning: more than 5000 data points")

        """  Calculate W statistic as squared correlation
        between data and coefficients """

        # sa /= n1
        # sx /= n1
        # ssa = ssx = sax = 0.0
        # j = n
        # for i in range(1, n1 + 1, 1):
        #     if i != j:
        #         asa = asigned[i - 1] - sa
        #     else:
        #         asa = -sa
        #     # print(asa)
        #     xsx = x[i - 1] / vrange - sx
        #     ssa += asa ** 2
        #     ssx += xsx ** 2
        #     sax += asa * xsx
        #     j -= 1

        # """  W1 equals (1-W) claculated to avoid excessive rounding error
        # for W very near 1 (a potential problem in very large samples) """

        # ssassx = np.sqrt(ssa * ssx)
        # w1 = (ssassx - sax) * (ssassx + sax) / (ssa * ssx)

        # print(asa)

    x__ = x - x.mean()
    # print()
    w = ((asigned * x).sum() ** 2) / (x ** 2).sum()
    w1 = 1 - w
    # print(w1, w_)

    # L70:

    # w = 1.0 - w1

    """  Calculate significance level for W """

    if n == 3:
        """exact P value :"""
        pw = pi6 * (np.arcsin(np.sqrt(w)) - stqr)
        return ShapiroResult(w, pw)

    y = np.log(w1)
    xx = np.log(an)
    m = 0.0
    s = 1.0
    if n <= 11:
        gamma = np.polyval(g, an)
        if y >= gamma:
            pw = small_value
            """ FIXME: rather use an even small_valueer value, or NA ? """
            return ShapiroResult(w, pw)

        y = -np.log(gamma - y)
        m = np.polyval(c3, an)
        s = np.exp(np.polyval(c4, an))
    else:
        """n >= 12"""
        m = np.polyval(c5, xx)
        s = np.exp(np.polyval(c6, xx))

    """DBG printf("c(w1=%g, w=%g, y=%g, m=%g, s=%g)\n",w1,*w,y,m,s) """

    if ncens > 0:
        """<==>  n > n1"""
        """  Censoring by proportion NCENS/N.
        Calculate mean and sd of normal equivalent deviate of W. """

        ld = -np.log(delta)
        bf = 1.0 + xx * bf1
        r__1 = xx90 ** xx
        z90f = z90 + bf * np.polyval(c7, r__1) ** ld
        r__1 = xx95 ** xx
        z95f = z95 + bf * np.polyval(c8, r__1) ** ld
        z99f = z99 + bf * np.polyval(c9, xx) ** ld

        """ Regress Z90F,...,Z99F on normal deviates Z90,...,Z99 to get
         * pseudo-mean and pseudo-sd of z as the slope and intercept 
         """

        zfm = (z90f + z95f + z99f) / 3.0
        zsd = (z90 * (z90f - zfm) + z95 * (z95f - zfm) + z99 * (z99f - zfm)) / zss
        zbar = zfm - zsd * zm
        m += zbar * s
        s *= zsd

    ppx = (y - m) / s

    pw = 1 - NormalDist().cdf(ppx)
    """  = alnorm_(dble((Y - M)/S), 1) """

    #  Results are returned in w, pw and ifault
    return ShapiroResult(w, pw)


def sign(x: int, y: int):
    if y < 0:
        return -abs(x)
    else:
        return abs(x)


if __name__ == "__main__":
    x = np.array(
        [
            0.139,
            0.157,
            0.175,
            0.256,
            0.344,
            0.413,
            0.503,
            0.577,
            0.614,
            0.655,
            0.954,
            1.392,
            1.557,
            1.648,
            1.690,
            1.994,
            2.174,
            2.206,
            3.245,
            3.510,
            3.571,
            4.354,
            4.980,
            6.084,
            8.351,
        ]
    )

    # np.random.seed(0)
    _x = np.sort(np.random.rand(50))
    _x = np.array([NormalDist().inv_cdf(_xi) for _xi in _x])
    # _x -= _x.mean()
    for offset, factor in zip([0, 0, 0.2, 0.5], [1, 2, 1, 3]):
        x = (_x + offset) * factor
        print(swilk(x))

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
