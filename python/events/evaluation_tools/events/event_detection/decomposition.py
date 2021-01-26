"""
================================
Event Detection :: Decomposition
================================
Use time series decomposition to detect hydroligical events in 
streamflow time series.

Functions
---------
detrend_streamflow
mark_event_flows
list_events

"""

import numpy as np
import pandas as pd

def detrend_streamflow(series, halflife, window, reverse=False) -> pd.Series:
    """Model the trend in a streamflow time series using a rolling 
        minimum filter. Remove the trend and residual components.
        Return the detrended streamflow time series.
        
        Parameters
        ----------
        series: pandas.Series with a DateTimeIndex, required
            The original streamflow time series.
        halflife: float, str, timedelta, required
            Specifies the decay term for `pandas.Series.ewm.mean`. This filter 
            is used to smooth over interevent noise and reduce detection 
            of normal instrument fluctuations as events.
        window: int, offset, or BaseIndexer subclass, required
            Size of the moving window for `pandas.Series.rolling.min`.
            This filter is used to model the trend in `series`.
        reverse: bool, default False, optional
            Specifies whether to run the filter in reverse.
            
        Returns
        -------
        detrended: pandas.Series
            New streamflow time series with trend removed.
        
        """
    # Flip series values to run filter in reverse
    if reverse:
        series = pd.Series(series.values[::-1], 
            index=series.index)

    # Smooth series
    smooth = series.ewm(halflife=halflife, times=series.index, 
        adjust=False).mean()
    
    # Estimate a seasonal trend using a rolling minimum
    trend = smooth.rolling(window=window).min()

    # Remove the seasonal trend
    detrended = smooth - trend

    # Assume a residual equal to twice the detrended median
    residual = detrended.median() * 2.0

    # Remove the residual
    detrended = detrended - residual

    # Eliminate negative values
    detrended[detrended < 0.0] = 0.0

    # Restore reversed series
    if reverse:
        # Return detrended series
        return pd.Series(detrended.values[::-1], 
            index=detrended.index)

    # Return detrended series
    return detrended

def mark_event_flows(series, halflife, window) -> pd.Series:
    """Model the trend in a streamflow time series by taking the mean
        of two rolling minimum filters applied in a forward and 
        backward fashion. Remove the trend and residual components.
        Return the boolean time series that indicates whether an 
        individual value in the original streamflow time series
        is part of an event (True) or not part of an event (False).
        
        Parameters
        ----------
        series: pandas.Series with a DateTimeIndex, required
            The original streamflow time series.
        halflife: float, str, timedelta, required
            Specifies the decay term for `pandas.Series.ewm.mean`. This filter 
            is used to smooth over interevent noise and reduce detection 
            of normal instrument fluctuations as events.
        window: int, offset, or BaseIndexer subclass, required
            Size of the moving window for `pandas.Series.rolling.min`.
            This filter is used to model the trend in `series`.
            
        Returns
        -------
        event_points: pandas.Series
            Boolean time series where True indicates the associated value
            in the `series` is part of an event.
        
        """
    # Detrend with a forward filter
    forward = detrend_streamflow(series, halflife, window)

    # Detrend with a backward filter
    backward = detrend_streamflow(series, halflife, window, True)

    # Take the mean of the forward and backward trends
    detrended = np.mean([forward, backward], axis=0)

    # Assume a residual equal to twice the detrended median
    residual = np.median(detrended) * 2.0

    # Remove the residual
    detrended = detrended - residual

    # Eliminate negative values
    detrended[detrended < 0.0] = 0.0

    # Return mask of non-zero detrended flows
    return pd.Series((detrended > 0.0), index=series.index)

def list_events(series, halflife, window) -> pd.DataFrame:
    """Apply time series decomposition to mark event values in a streamflow
        time series. Discretize continuous event values into indiviual events.
        Return a DataFrame with one row for each event detected with `start` and 
        `end` columns indicating the boundaries of each event.
        
        Parameters
        ----------
        series: pandas.Series with a DateTimeIndex, required
            The original streamflow time series.
        halflife: float, str, timedelta, required
            Specifies the decay term for `pandas.Series.ewm.mean`. This filter 
            is used to smooth over interevent noise and reduce detection 
            of normal instrument fluctuations as events.
        window: int, offset, or BaseIndexer subclass, required
            Size of the moving window for `pandas.Series.rolling.min`.
            This filter is used to model the trend in `series`.
            
        Returns
        -------
        events: pandas.DataFrame
            A two column DataFrame with a row for each event detected. `start` and 
            `end` columns indicate the boundaries of each event.
        
        """
    # Detect event flows
    events = mark_event_flows(series, halflife, window)

    # Identify event starts
    forward_shift = events.shift(1).fillna(False)
    starts = (events & ~forward_shift)
    starts = starts[starts]

    # Identify event ends
    backward_shift = events.shift(-1).fillna(False)
    ends = (events & ~backward_shift)
    ends = ends[ends]

    # Extract times
    return pd.DataFrame({
        'start': starts.index,
        'end': ends.index
    })
    