# Evaluation Tools

Tools for retrieving and evaluating hydrological data.

## Motivation

We developed evaluation_tools with data scientists in mind. We attempted to ensure
the simplest methods such as `get` both accepted and returned data structures
frequently used by data scientists using scientific Python. Specifically, this means
that
[`pandas.DataFrames`](https://pandas.pydata.org/docs/user_guide/dsintro.html#dataframe),
[`geopandas.GeoDataFrames`](https://geopandas.readthedocs.io/en/latest/docs/user_guide/data_structures.html#geodataframe),
and
[`numpy.arrays`](https://numpy.org/doc/stable/reference/arrays.html#array-objects)
are the most frequently encountered data structures when using evaluation_tools. The
majority of methods include sensible defaults that cover the majority of use-cases,
but allow customization if required.

We also attempted to adhere to organizational (NOAA-OWP) data standards where they
exist. This means `pandas.DataFrames` will contain column labels like
`usgs_site_code`, `start_date`, `value_date`, and `measurement_unit` which are
consistent with organization wide naming conventions. Our intent is to make
retrieving, evaluating, and exporting data as easy and reproducible as possible for
scientists, practitioners and other hydrological experts.

## What's here?

We've taken a grab-and-go approach to installation and usage of Evaluation tools.
This means, in line with a standard toolbox, you will typically install just the tool
or tools that get your job done without having to install all the other tools
available. This means a lighter installation load and that tools can be added to the
toolbox, without affecting your workflows!

It should be noted, we commonly refer to individual tools in evaluation tools as a
subpackage or by their name (e.g. `nwis_client`). You will find this lingo in both
issues and documentation.

Currently the repository has the following subpackages:

- nwis_client: Provides easy to use methods for retrieving data from the [USGS NWIS
  Instantaneous Values (IV) Web
  Service](https://waterservices.usgs.gov/rest/IV-Service.html).
- \_restclient: A generic REST client with built in cache that make the construction
  and retrieval of GET requests painless.
- events: Variety of methods used to perform event-based evaluations of hydrometric time series.

## UTC Time

Note: the canonical `pandas.DataFrames` used by evaluation_tools use time-zone naive
datetimes that assume UTC time. In general, do not assume methods are compatible with
time-zone aware datetimes or timestamps. Expect methods to transform time-zone aware
datetimes and timestamps into their timezone naive counterparts at UTC time.

## Usage

### NWIS IV Client Example
```python
# Import the NWIS IV Client
from evaluation_tools.nwis_client.iv import IVDataService

# Retrieve data from a single site
observations_data = IVDataService.get(
    sites='01646500', 
    startDT='2019-08-01', 
    endDT='2020-08-01'
    )

# Look at the data
print(observations_data.head())

           value_date variable_name usgs_site_code measurement_unit   value qualifiers  series
0 2019-08-01 04:00:00    streamflow       01646500            ft3/s  4170.0        [A]       0
1 2019-08-01 04:15:00    streamflow       01646500            ft3/s  4170.0        [A]       0
2 2019-08-01 04:30:00    streamflow       01646500            ft3/s  4170.0        [A]       0
3 2019-08-01 04:45:00    streamflow       01646500            ft3/s  4170.0        [A]       0
4 2019-08-01 05:00:00    streamflow       01646500            ft3/s  4170.0        [A]       0
```

### Event Detection Example
```python
# Import tools to retrieve data and detect events
from evaluation_tools.nwis_client.iv import IVDataService
from evaluation_tools.events.event_detection import decomposition as ev

# Use pandas to resample the data
from pandas import Grouper

# Use a helper function to detect events at multiple sites
def list_events_helper(mi_series, level, halflife, window):
    """Reduce multi-index series before applying event detection."""
    return ev.list_events(mi_series.droplevel(level), halflife, window)

# Retrieve streamflow observations for two sites
observations = IVDataService.get(
    sites='02146750,0214676115,09489000', 
    startDT='2019-10-01', 
    endDT='2020-09-30'
    )

# Drop extra columns to be more efficient
observations = observations[[
    'usgs_site_code', 
    'value_date', 
    'value'
    ]]

# Check for duplicate time series, keep first by default
observations = observations.drop_duplicates(
    subset=['usgs_site_code', 'value_date']
    )

# Resample to hourly, keep first measurement in each 1-hour bin
observations = observations.groupby([
    'usgs_site_code',
    Grouper(key='value_date', freq='H')
    ]).first().ffill()

# Detect events
events = observations['value'].groupby(
    level='usgs_site_code').apply(
        list_events_helper, 
        level='usgs_site_code', 
        halflife='6H', 
        window='7D'
    )

# Print event list    
print(events)

                                start                 end
usgs_site_code                                           
02146750       0  2019-10-13 22:00:00 2019-10-15 04:00:00
               1  2019-10-16 09:00:00 2019-10-18 02:00:00
               2  2019-10-19 03:00:00 2019-10-23 19:00:00
               3  2019-10-27 05:00:00 2019-10-28 18:00:00
               4  2019-10-30 01:00:00 2019-11-02 18:00:00
...                               ...                 ...
09489000       34 2020-09-16 00:00:00 2020-09-16 19:00:00
               35 2020-09-17 00:00:00 2020-09-17 15:00:00
               36 2020-09-18 04:00:00 2020-09-18 10:00:00
               37 2020-09-27 01:00:00 2020-09-27 03:00:00
               38 2020-09-28 05:00:00 2020-09-28 11:00:00
```

### Metrics Example
```python
from evaluation_tools.metrics import metrics
from evaluation_tools.nwis_client.iv import IVDataService
import pandas as pd

# Get observed data
observed = IVDataService.get(
    sites='01646500',
    startDT='2020-01-01',
    endDT='2021-01-01'
    )

# Preprocess data
observed = observed[['value_date', 'value']]
observed = observed.drop_duplicates(['value_date'])
observed = observed.set_index('value_date')
observed = observed.resample('H').nearest()

# Simulate a 10-day persistence forecast
issue_frequency = pd.Timedelta('6H')
forecast_length = pd.Timedelta('10D')
forecasts = observed.resample(issue_frequency).nearest()

# Apply flood criteria using a "Hit Window" approach
#  A flood is observed or simluated if any value within the
#  forecast_length meets or exceeds the flood_criteria
# 
# Apply flood_criteria to forecasts
flood_criteria = 19200.0
forecasts['simulated_flood'] = (forecasts['value'] >= flood_criteria)

# Apply flood_criteria to observations
for row in forecasts.itertuples():
    obs = observed.loc[row.Index:row.Index+forecast_length, 'value'].max()
    observed.loc[row.Index, 'observed_flood'] = (obs >= flood_criteria)

# Drop non-forecast times
observed = observed.dropna()

# Convert boolean columns to Categoricals
forecasts['simulated_flood'] = forecasts['simulated_flood'].astype('category')
observed['observed_flood'] = observed['observed_flood'].astype('category')

# Compute contingency table
contingency_table = metrics.compute_contingency_table(
    observed['observed_flood'],
    forecasts['simulated_flood']
)
print('Contingency Table Components')
print('============================')
print(contingency_table)

# Compute threat score/critical success index
TS = metrics.threat_score(contingency_table)
print('Threat Score: {:.2f}'.format(TS))

Contingency Table Components
============================
true_positive      148
false_positive     194
false_negative       0
true_negative     1123
dtype: int64
Threat Score: 0.43
```

## Installation

In accordance with the python community, we support and advise the usage of virtual
environments in any workflow using python. In the following installation guide, we
use python's built-in `venv` module to create a virtual environment in which the
tools will be installed. Note this is just personal preference, any python virtual
environment manager should work just fine (`conda`, `pipenv`, etc. ).

```bash
# Create and activate python environment, requires python >= 3.8
$ python3 -m venv venv
$ source venv/bin/activate
$ python3 -m pip install --upgrade pip

# Install nwis_client
$ python3 -m pip install git+https://github.com/NOAA-OWP/evaluation_tools.git#subdirectory=python/nwis_client

# Install _restclient
$ python3 -m pip install git+https://github.com/NOAA-OWP/evaluation_tools.git#subdirectory=python/_restclient

# Install events
$ python3 -m pip install git+https://github.com/NOAA-OWP/evaluation_tools.git#subdirectory=python/events
```

## Documentation

[Evaluation tools](https://noaa-owp.github.io/evaluation_tools/) GitHub pages documentation
