Solar calculator
==============

Simulates the performance of a solar installation with optional battery storage. It combines solar PVGIS data with tariff and historical consumption to generate as accurate a simulation as possible. The longer term plan is to develop a Home Assistant plugin to implement the same storage strategy on actual consumption.

Installation
------------

### Windows release
There is a Windows release available which includes a built in Python interpreter. Take a look at the releases page.
To use the release version, simply unzip solar.zip and run solar.exe. Note that the realeas may well not be the most recent version.

### Windows and other operating systems

Install Python if you don't already have a copy installed. If you are installing on Windows make sure you enable 'Add python.exe to PATH' when you run the installer.


From a terminal enter:
```
pip install pysimplegui iso8601
```
Most of the other libraries needed by solar sim should come as standard with Python.

Download the Git repository, navigate to the directory wher you downloaded it and run solar.py:
```
python solar.py
```

Quick start
-----------

In Solar calculator click on 'Load config' and select one of the demo configs in the demos folder. Now hit 'Run' to run the simulation. A summary wil be shown on the log and two CSV files wil lbe created. The summary contains the monthly summary and full contains the full simulation in 30 minute increments. The full simulation is useful for tweaking your storage strategy.

Getting your own solar string data
----------------------------------

Go to the Europa PVGIS tool https://re.jrc.ec.europa.eu/pvg_tools/en/ and select 'Hourly data'. Click on the world map to place a pin on your location. For the start year select a few years in the past. For the end date select the most recent date. You want at least 2 years.
Set the mounting tipe and angles to suit your installation. Turn on 'PV power' and enter the details of your system. Now click on the json download button. If you have multiple strings at different angles, repeat for each string. For the 'Max MPPT' value enter the maximum inverter input power for that string. If you don't know this value you can make an estimate by dividing the inverter output power by the number of strings it can support.

CSV files
---------

Solar calculator is configured to import most styles of CSV files. If the CSV file contains column names in the first row enter the column names you are interested in. If not, use the column indexes, the first column is 0, the second is 1 and so on. If your import/export pricing is in pence/cents turn on 'divide by 100' to convert to pounds/dollars.

Tariff data
-----------

For simple tariffs that are the same each day you can create your own tariff csv file. Take a look at the 'octopus cosy south west' demo csv file for an example. The file just needs one column for the date/time and one column for the prices. You must start with the price for the time 00:00. You can have extra columns, for instance you may want to have import and export in the same file. For more complex tariff such as Octopus agile you may be able to download historical data. A useful source of Octopus Energy data is https://energy-stats.uk/

Historical consumption
----------------------

If you are a data hoarder and have full hourly or half hourly historical data, that is the best data to use. It just needs to be in CSV format with at least a date column and an energy usage column. In this case you can ignore the usage modifier. If not, look at your electricity bills and create a CSV file containing each month's usage. Be careful to enter the usage and the exact date that usage was calculated. Simple monthly data is not adequate so you need to add a daily consumption modifier. This adds the pattern of usage thoughout the day. Take a look at the demo 'daily usage working daytime' csv file as an example. The values are all normalised to fit the day's calculated consumption so only the shape of the curve matters, not the absolute values. If you can monitor your usage throughout one average day you will be fairly close, though of course the pattern vaires thoughout the year.

Storage strategies
------------------

Currently there is only one storage strategy - 'Rules'. This lets you define rules for when to charge/discharge the battery. In the future extra strategies may be added. For instance it would be interesting to add a machine learning based strategy that tries to automatically optimise storage for traiffs that are based on grid pricing.

For more information on strategies, look at the text files in the strategies folder.

