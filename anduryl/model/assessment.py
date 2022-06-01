from anduryl.core.metalog import get_valid_metalog, get_valid_5p_metalog
import numpy as np


class Assessment:
    def __init__(self, quantiles, values, expertid, itemid, scale, observer=None):
        self.expertid = expertid
        self.itemid = itemid
        self.scale = scale
        assert len(quantiles) == len(values)
        self._estimates = dict(zip(quantiles, values))
        self._observer = observer

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


class MetalogAssessment(Assessment):
    def __init__(self, quantiles, values, expertid, itemid, scale, observer=None):
        super().__init__(
            quantiles=quantiles,
            values=values,
            expertid=expertid,
            itemid=itemid,
            scale=scale,
            observer=observer,
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
            self.fit_metalog()
        return self._metalog

    def set_value(self, quantile, estimate):
        super().set_value(quantile, estimate)

    def fit_metalog(self):
        xs = list(self._estimates.values())
        if np.isnan(xs).any():
            self._metalog = NaNDist()
            return
        # print(f"Fitting metalog for {self.itemid} {self.expertid} {xs}")
        if self.scale == "log":
            xs = np.log(xs)
        if len(xs) == 3:
            self._metalog = get_valid_metalog(ps=list(self._estimates.keys()), xs=xs)
        elif len(xs) == 5:
            self._metalog = get_valid_5p_metalog(ps=list(self._estimates.keys()), xs=xs)
        else:
            raise NotImplementedError()

    def ppf(self, p):
        x = self.metalog.ppf(p)
        if self.scale == "log":
            x = np.exp(np.clip(x, -708, 708))
        return x

    def cdf(self, x):
        if self.scale == "log":
            x = np.log(x)
        return self.metalog.cdf(x)


def inextrp1d(x, xp, fp):
    """
    Interpolate an array along the given axis.
    Similar to np.interp, but with extrapolation outside range.

    Parameters
    ----------
    x : np.array
        Array with positions to interpolate at
    xp : np.array
        Array with positions of known values
    fp : np.array
        Array with values as known positions to interpolate between

    Returns
    -------
    np.array
        interpolated array
    """
    # Determine lower bounds
    intidx = np.minimum(np.maximum(0, np.searchsorted(xp, x) - 1), len(xp) - 2)
    # Determine interpolation fractions
    fracs = (x - xp[intidx]) / (xp[intidx + 1] - xp[intidx])
    # Interpolate (1-frac) * f_low + frac * f_up
    f = (1 - fracs) * fp[intidx] + fp[intidx + 1] * fracs

    return f


class NaNDist:
    def __init__(self):
        self.pps = np.array([])
        self.prange = np.array([])


class EmpiricalAssessment(Assessment):
    def __init__(self, quantiles, values, expertid, itemid, scale, observer=None):
        super().__init__(
            quantiles=quantiles,
            values=values,
            expertid=expertid,
            itemid=itemid,
            scale=scale,
            observer=observer,
        )

        # Prepare arrays for interpolation
        quantiles, index = np.unique(quantiles, return_index=True)
        values = values[index]
        values, index = np.unique(values, return_index=True)
        quantiles = quantiles[index]

        self.fp = np.concatenate([[0.0], quantiles, [1.0]])
        if scale == "log":
            values = np.log(values)

        self.xp = np.concatenate(
            [
                [inextrp1d(0.0, quantiles, values)],
                values,
                [inextrp1d(1.0, quantiles, values)],
            ]
        )

    def cdf(self, x):
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
