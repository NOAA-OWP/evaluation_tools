"""
================================
Event Detection :: Decomposition
================================
Use time series decomposition to detect hydroligical events in 
streamflow time series as described in Regina & Ogden, 2020.

Regina, J.A., F.L. Ogden, 2020.  Automated Correction of Systematic 
    Errors in High-Frequency Stage Data from V-Notch Weirs using 
    Time Series Decomposition., Under review., Hydrol. Proc.

Functions
---------
detrend_streamflow
mark_event_flows
list_events

"""

import numpy as np
import pandas as pd
from typing import Union
import datetime

def detrend_streamflow(
    series: pd.Series,
    halflife: Union[float, str, pd.Timedelta],
    window: Union[int, pd.tseries.offsets.DateOffset, pd.Index],
    reverse: bool =False
    ) -> pd.Series:
    """Model the trend in a streamflow time series using a rolling 
        minimum filter. Remove the trend and residual components. The method 
        aims to produce a detrended time series with a median of 0.0. It assumes 
        any residual components less than twice the detrended median are random 
        noise.
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

def event_boundaries(event_points: pd.Series):
    """Return a two column pandas.DataFrame with 'start' and 'end' event times
        generated from a time series of boolean event points.
        
        Parameters
        ----------
        event_points: pandas.Series
            Boolean time series where True indicates the associated value
            in the `series` is part of an event.

        Returns
        -------
        events: pandas.DataFrame
            A two column DataFrame with a row for each event detected. `start` and 
            `end` columns indicate the boundaries of each event.
        
        """
    # Identify event starts
    forward_shift = event_points.shift(1).fillna(False)
    starts = (event_points & ~forward_shift)
    starts = starts[starts]

    # Identify event ends
    backward_shift = event_points.shift(-1).fillna(False)
    ends = (event_points & ~backward_shift)
    ends = ends[ends]

    # Extract times
    return pd.DataFrame({
        'start': starts.index,
        'end': ends.index
    })

def mark_event_flows(
    series: pd.Series,
    halflife: Union[float, str, pd.Timedelta],
    window: Union[int, pd.tseries.offsets.DateOffset, pd.Index],
    minimum_event_duration: Union[pd.Timedelta, datetime.timedelta, np.timedelta64, str, int] = '0H'
    ) -> pd.Series:
    """Model the trend in a streamflow time series by taking the max
        of two rolling minimum filters applied in a forward and 
        backward fashion. Remove the trend and residual components. The method 
        aims to produce a detrended time series with a median of 0.0. It assumes 
        any residual components less than twice the detrended median are random 
        noise.
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
        minimum_event_duration: pandas.Timedelta, datetime.timedelta, numpy.timedelta64, str, int, optional, default '0H'
            Enforce a minimum event duration. This should generally be set equal to 
            halflife to reduce the number of false positives flagged as events.
            
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

    # Take the max of the forward and backward trends
    detrended = np.maximum(forward, backward)

    # Assume a residual equal to twice the detrended median
    residual = np.median(detrended) * 2.0

    # Remove the residual
    detrended = detrended - residual

    # Eliminate negative values
    detrended[detrended < 0.0] = 0.0
    
    # Generate mask of non-zero detrended flows
    event_points = pd.Series((detrended > 0.0), index=series.index)

    # Do not filter events
    minimum_event_duration = pd.Timedelta(minimum_event_duration)
    if minimum_event_duration == pd.Timedelta(0):
        # Return mask of non-zero detrended flows
        return event_points

    # Get list of potential events
    events = event_boundaries(event_points)

    # Compute durations
    durations = events['end'].sub(events['start'])

    # Filter events
    events = events[durations >= minimum_event_duration].reset_index(drop=True)
    
    # Refine event points
    filtered_event_points = pd.Series(data=False, index=event_points.index)
    for e in events.itertuples():
        filtered_event_points.loc[e.start:e.end] = True
    
    # Return filtered event points
    return filtered_event_points

def list_events(
    series: pd.Series,
    halflife: Union[float, str, pd.Timedelta],
    window: Union[int, pd.tseries.offsets.DateOffset, pd.Index],
    minimum_event_duration: Union[pd.Timedelta, datetime.timedelta, np.timedelta64, str, int] = '0H'
    ) -> pd.DataFrame:
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
        minimum_event_duration: pandas.Timedelta, datetime.timedelta, numpy.timedelta64, str, int, optional, default '0H'
            Enforce a minimum event duration. This should generally be set equal to 
            halflife to reduce the number of false positives flagged as events.
            
        Returns
        -------
        events: pandas.DataFrame
            A two column DataFrame with a row for each event detected. `start` and 
            `end` columns indicate the boundaries of each event.
        
        """
    # Detect event flows
    event_points = mark_event_flows(series, halflife, window, minimum_event_duration)

    # Return events
    return event_boundaries(event_points)
