import xarray as xr
import matplotlib.pyplot as plt


@xr.register_dataset_accessor("qc")
class QCAccessor:
    def __init__(self, ds):
        self._ds = ds

    def _flag_var(self, var):
        return self._ds[var].attrs["ancillary_variables"]

    def set_flag(self, var, flag_value, where):
        """Flag values matching a boolean mask, leaving data untouched."""
        qc_var = self._flag_var(var)
        self._ds[qc_var] = self._ds[qc_var].where(~where, flag_value)
        return self._ds

    def edit_value(self, var, new_value, where, flag_value=4):
        """Correct/despike a value and flag it in the same call."""
        qc_var = self._flag_var(var)
        self._ds[var] = self._ds[var].where(~where, new_value)
        self._ds[qc_var] = self._ds[qc_var].where(~where, flag_value)
        return self._ds

    def masked(self, var, keep_flags=(1, 2)):
        """Return the data with bad-flagged points as NaN."""
        qc_var = self._flag_var(var)
        return self._ds[var].where(self._ds[qc_var].isin(keep_flags))

    def check_sensor_agreement(self, var, threshold, flag_value=3):
        """Flag scans where primary/secondary sensors diverge beyond threshold."""
        diff = abs(
            self._ds[var].sel(sensor="primary")
            - self._ds[var].sel(sensor="secondary")
        )
        bad = diff > threshold
        qc_var = self._flag_var(var)
        self._ds[qc_var].loc[dict(sensor="primary")] = (
            self._ds[qc_var].sel(sensor="primary").where(~bad, flag_value)
        )
        self._ds[qc_var].loc[dict(sensor="secondary")] = (
            self._ds[qc_var].sel(sensor="secondary").where(~bad, flag_value)
        )
        return self._ds

    def best_estimate(self, var, prefer="primary", keep_flags=(1, 2)):
        """Pick primary unless flagged bad, falling back to secondary."""
        primary = self._ds[var].sel(sensor="primary")
        secondary = self._ds[var].sel(sensor="secondary")
        primary_qc = self._ds[self._flag_var(var)].sel(sensor=prefer)
        return primary.where(primary_qc.isin(keep_flags), secondary)


@xr.register_dataset_accessor("ctd")
class CTDPlotAccessor:
    def __init__(self, ds):
        self._ds = ds

    def profile(self, var, sensor=None, qc_mask=True, ax=None, **kwargs):
        """Plot var vs pressure, oceanographic convention (pressure down)."""
        ax = ax or plt.gca()
        da = self._ds[var]

        if "sensor" in da.dims:
            if sensor is not None:
                da = da.sel(sensor=sensor)
            else:
                for s in self._ds.sensor.values:
                    self._ds.ctd.profile(
                        var, sensor=s, ax=ax, qc_mask=qc_mask, **kwargs
                    )
                ax.invert_yaxis()
                ax.legend()
                return ax

        if qc_mask:
            da = self._ds.qc.masked(var)

        ax.plot(da, self._ds.pressure, **kwargs)
        ax.invert_yaxis()
        ax.set_xlabel(
            f"{da.attrs.get('long_name', var)} ({da.attrs.get('units', '')})"
        )
        ax.set_ylabel("Pressure (dbar)")
        return ax

    def flagged(self, var, ax=None):
        """Highlight good vs flagged points."""
        ax = ax or plt.gca()
        good = self._ds[self._flag_var(var)].isin([1, 2])
        ax.plot(
            self._ds[var].where(good), self._ds.pressure, ".", label="good"
        )
        ax.plot(
            self._ds[var].where(~good),
            self._ds.pressure,
            "x",
            color="C3",
            label="flagged",
        )
        ax.invert_yaxis()
        ax.legend()
        return ax
