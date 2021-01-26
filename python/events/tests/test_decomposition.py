import pytest
from evaluation_tools.events.event_detection import decomposition as ev

def test_list_events():
    # Create trend
    t = np.linspace(1.0, 1001.0, 1000)
    trend = 100.0 * np.exp(-0.002 * t)

    # Create event
    zero_flows = np.zeros(500)
    event_flows = 1000.0 * np.exp(-0.004 * t[:500])
    event_flows = np.concatenate([zero_flows, event_flows])

    # Sum total flow
    flow = trend + event_flows

    # Create streamflow time series
    series = pd.Series(
        flow,
        index=pd.date_range(
            start=pd.to_datetime('2018-01-01'),
            periods=len(t),
            freq='H'),
        name='streamflow'
    )

    # Detect event
    events = ev.list_events(series, '6H', '7D')

    # Should detect a single event
    assert len(events.index) == 1
