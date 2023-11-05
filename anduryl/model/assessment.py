from anduryl.core.metalog import get_valid_metalog, get_valid_5p_metalog
from anduryl.core.calculate import inextrp1d
import numpy as np
from typing import Union

from anduryl.io.settings import Distribution


class Assessment:
    def __init__(
        self,
        quantiles,
        values,
        expertid,
        itemid,
        scale,
        observer=None,
        item_lbound=None,
        item_ubound=None,
    ):
        # TODO: Check updating on changes
        self.expertid = expertid
        self.itemid = itemid
        self.scale = scale
        assert len(quantiles) == len(values)
        self._estimates = dict(zip(quantiles, values))
        self._observer = observer
        self.item_lbound = item_lbound
        self.item_ubound = item_ubound

    def set_value(self, quantile, estimate):
        self._estimates[quantile] = estimate
        self._observer(
            {"expertid": self.expertid, "itemid": self.itemid, "quantile": quantile, "value": estimate}
        )

    @property
    def estimates(self):
        return self._estimates

    @estimates.setter
    def estimates(self, dct):
        self._estimates.clear()
        for p, val in dct.items():
            self.set_value(quantile=p, estimate=val)

    def bind_to(self, callback):
        self._observers.append(callback)


# class PWLAssessment(Assessment):
#     def __init__(self, quantiles, values, expertid, itemid, scale, observer=None):
#         super().__init__(
#             quantiles=quantiles,
#             values=values,
#             expertid=expertid,
#             itemid=itemid,
#             scale=scale,
#             observer=observer,
#         )

#     def information(self, lower, upper):

#         pass


class ExpertAssessment(Assessment):
    def __init__(
        self,
        quantiles,
        values,
        expertid,
        itemid,
        scale,
        observer=None,
        item_lbound=None,
        item_ubound=None,
    ):
        super().__init__(
            quantiles=quantiles,
            values=values,
            expertid=expertid,
            itemid=itemid,
            scale=scale,
            observer=observer,
            item_lbound=item_lbound,
            item_ubound=item_ubound,
        )
        self._metalog = None

    @property
    def estimates(self):
        return self._estimates

    @estimates.setter
    def estimates(self, dct):
        super().estimates(dct)

    @property
    def metalog(self):
        if self._metalog is None:
            self._fit_metalog()
        return self._metalog        

    def plot(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(self._metalog.pps, self._metalog.prange, marker='.')
        ax.grid()
        plt.show()

    def set_value(self, quantile, estimate):
        super().set_value(quantile, estimate)

    def _fit_metalog(self):
        xs = list(self._estimates.values())
        if np.isnan(xs).any():
            self._metalog = NaNDist()
            return
        # print(f"Fitting metalog for {self.itemid} {self.expertid} {xs}")
        ps = list(self._estimates.keys())
        if self.scale == "log":
            xs = np.log(xs)
        
        # If not known, fit a new one    
        if len(xs) == 3:
            self._metalog = get_valid_metalog(
                ps=ps,
                xs=xs,
                item_lbound=self.item_lbound,
                item_ubound=self.item_ubound,
            )
        elif len(xs) == 5:
            self._metalog = get_valid_5p_metalog(
                ps=ps,
                xs=xs,
                item_lbound=self.item_lbound,
                item_ubound=self.item_ubound,
            )
        else:
            raise NotImplementedError('A different number of percentiles than 3 or 5 is not Implemented')
        
            
    def ppf(self, p: float, distribution: Distribution, lower: bool=None, upper: bool=None):
        if distribution == Distribution.PWL:
            return self._ppf_pwl(p, lower, upper)
        elif distribution == Distribution.METALOG:
            return self._ppf_metalog(p)

    def cdf(self, x: float, distribution: Distribution, lower: Union[float, None], upper: Union[float, None]):
        if distribution == Distribution.PWL:
            return self._cdf_pwl(x, lower, upper)
        elif distribution == Distribution.METALOG:
            return self._cdf_metalog(x)

    def information(self, lower: float, upper: float, distribution: Distribution):
        if distribution == Distribution.PWL:
            return self._information_pwl(lower, upper)
        elif distribution == Distribution.METALOG:
            return self._information_metalog(lower, upper)

    def _cdf_pwl(self, x, lower, upper):
        values = list(self._estimates.values())
        if self.scale == 'log':
            values = np.log(values)
            x = np.log(x)
        
        return np.interp(
            x,
            np.concatenate([[lower], values, [upper]]),
            np.concatenate([[0.0], list(self._estimates.keys()), [1.0]]),
        )

    def _ppf_pwl(self, p, lower, upper):
        values = list(self._estimates.values())
        if self.scale == 'log':
            values = np.log(values)
            
        return np.interp(
            p,
            np.concatenate([[0.0], list(self._estimates.keys()), [1.0]]),
            np.concatenate([[lower], values, [upper]]),
        )

    def _ppf_metalog(self, p):
        x = self.metalog.ppf(p)
        if self.scale == "log":
            x = np.exp(np.clip(x, -708, 708))
        return x

    def _cdf_metalog(self, x):
        if self.scale == "log":
            x = np.log(x)
        return self.metalog.cdf(x)

    def _information_metalog(self, lower, upper):
        # TODO: Use the bounds in a neater way?
        # cdvs = self.metalog.prange
        # pps = self.metalog.pps
        # # Get the percentile points in between the pre-calculated values
        # # midpoints = np.concatenate([[pps[0]], (pps[1:] + pps[:-1]) / 2, [pps[-1]]])

        # # Calculate the expected probability (p)
        # # From the midpoint of the percentile range, encapsulated by 0 and 1
        # mp = np.concatenate([[0.0], (cdvs[1:] + cdvs[:-1]) / 2, [1.0]])
        # # Get the difference to get probability masss
        # p = mp[1:] - mp[:-1]

        # # Calculate the observed probabilities for the same bins
        # # by interpolating the minpoints in the 
        # s = inextrp1d(x=mp, xp=cdvs, fp=pps)
        # s = s[1:] - s[:-1]

        # # The information score is only calculated for the part within the intrinsic range
        # inrange = (pps > lower) & (pps < upper)
        # info1 = np.log(upper - lower) + np.sum(p[inrange] * np.log(p[inrange] / s[inrange]))

        cdvs = self.metalog.prange
        pps = self.metalog.pps
        
        # Modify the pps such that they span the full bounds
        _cdvs = np.unique(np.concatenate([[self.metalog.cdf(lower), self.metalog.cdf(upper)], cdvs]))
        _pps = np.unique(np.concatenate([[lower, upper], pps]))

        # The information score is only calculated for the part within the intrinsic range
        inrange = (_pps >= lower) & (_pps <= upper)
        _cdvs = _cdvs[inrange]
        _pps = _pps[inrange]

        # Calculate the expected (background) probability
        p = _cdvs[1:] - _cdvs[:-1]
        # Correct the score for only considering the part between lower and upper
        p /= p.sum()

        # Calculate the expert assigned range (from metalog)
        dx = _pps[1:] - _pps[:-1]
        # Calculate information score
        info2 = np.log(upper - lower) + np.sum(p * np.log(p / dx))


        # BELOW A VALIDATION BASED ON LIMITING A PIECE-WISE UNIFORM DIST
        # pps = np.array([0, 5, 45, 50, 55, 95, 100])
        # cdf = np.array([0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0])

        # # _pps = pps
        # # _cdf = cdf

        # p = cdf [1:] - cdf[:-1]
        # p /= p.sum()
        # s = pps [1:] - pps[:-1]

        # I = np.log(pps[-1] - pps[0]) + np.sum(p * np.log(p / s))
        # print(I)


        # _pps = np.concatenate([[2], pps[1:-1], [98]])
        # _cdf = np.interp(_pps, pps, cdf)

        
        # p = _cdf [1:] - _cdf[:-1]
        # p /= p.sum()
        # s = _pps [1:] - _pps[:-1]

        # I = np.log(_pps[-1] - _pps[0]) + np.sum(p * np.log(p / s))
        # print(I)

        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots()
        # ax.plot(pps, cdf)
        # ax.plot(_pps, _cdf)
        # plt.show()
        



        return info2


class NaNDist:
    def __init__(self):
        self.pps = np.array([])
        self.prange = np.array([])


class EmpiricalAssessment(Assessment):
    def __init__(
        self,
        quantiles,
        values,
        expertid,
        itemid,
        scale,
        observer=None,
        item_lbound=None,
        item_ubound=None,
    ):
        super().__init__(
            quantiles=quantiles,
            values=values,
            expertid=expertid,
            itemid=itemid,
            scale=scale,
            observer=observer,
            item_lbound=item_lbound,
            item_ubound=item_ubound,
        )

        # Prepare arrays for interpolation
        values, index = np.unique(values, return_index=True)
        quantiles = quantiles[index]
        # print(values, quantiles)
        # Remove out of bound values (inaccuracies)
        index = ((quantiles >= 0.0) & (quantiles <= 1)) | np.isnan(quantiles)
        quantiles = quantiles[index]
        values = values[index]
        # quantiles = np.clip(quantiles, 0, 1)
        quantiles, index = np.unique(quantiles, return_index=True)
        # If values are not in ascending order, 
        values = values[index]

        neg = (np.diff(values) < 0)
        k = 0
        while neg.any():
            idx = np.concatenate([[True], ~neg])
            values = values[idx]
            quantiles = quantiles[idx]
            neg = (np.diff(values) < 0)
            k+=1
            print(k)
        
        self.fp = np.concatenate(
            [
                [0.0] if 0.0 not in quantiles else [],
                quantiles,
                [1.0] if 1.0 not in quantiles else [],
            ]
        )
        if scale == "log":
            values = np.log(values)

        self.xp = np.concatenate(
            [
                [inextrp1d(0.0, quantiles, values)] if 0.0 not in quantiles else [],
                values,
                [inextrp1d(1.0, quantiles, values)] if 1.0 not in quantiles else [],
            ]
        )

        self.s = self.xp[1:] - self.xp[:-1]
        self.p = self.fp[1:] - self.fp[:-1]

# import matplotlib.pyplot as plt
# fig, ax = plt.subplots()
# ax.plot(self.s, self.p)
# plt.show()

        if (self.s < 0.0).any():
            raise ValueError()
        
        if (self.p < 0.0).any():
            raise ValueError()
        

    def cdf(self, x: float, distribution: Distribution, lower: float, upper: float):
        if self.scale == "log":
            x = np.log(x)
        return np.interp(x, self.xp, self.fp)

    def ppf(self, p):
        # Interpolate probability in cdf curve
        x = np.interp(p, self.fp, self.xp)
        if self.scale == "log":
            # If log-scale, the xp values are saved log-transformed
            # Transform interpolated x-value with exp
            x = np.exp(x)
        return x

    def information(self, lower: float, upper: float, distribution: Distribution):

        # Observed and expected
        mp = (self.xp[1:] + self.xp[:-1]) * 0.5

        # The information score is only calculated for the part within the intrinsic range
        inrange = (mp > lower) & (mp < upper) & (self.s > 0)
        frac = self.p[inrange] / self.s[inrange]
        # if (frac < 0.0).any():
            # raise ValueError()
        info = np.log(upper - lower) + np.sum(self.p[inrange] * np.log(frac))

        # cdvs = np.concatenate([[0.001], np.linspace(0.0, 1.0, 301)[1:-1], [0.999]])
        # pps = inextrp1d(x=cdvs, xp=self.fp, fp=self.xp)
        # # Get the percentile points in between the pre-calculated values
        # # midpoints = np.concatenate([[pps[0]], (pps[1:] + pps[:-1]) / 2, [pps[-1]]])

        # # Calculate the expected probability (p)
        # mp = np.concatenate([[0.0], (cdvs[1:] + cdvs[:-1]) / 2, [1.0]])
        # p = mp[1:] - mp[:-1]

        # # Calculate the observed probabilities for the same bins
        # s = inextrp1d(x=mp, xp=cdvs, fp=pps)
        # s = s[1:] - s[:-1]

        # # The information score is only calculated for the part within the intrinsic range
        # inrange = (pps > lower) & (pps < upper)
        # info2 = np.log(upper - lower) + np.sum(p[inrange] * np.log(p[inrange] / s[inrange]))

        # print(f'{info:.3f} - {info2:.3f} - {info - info2:.5g}')

        return info
