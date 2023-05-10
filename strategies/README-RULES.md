# Using the 'rules' strategy

This strategy simulates a hybrid inverter. You can specify when to charge/discharge the battery depending on a set uf rules. It also allow you to specify 'intelligent' loads that can be switched on when excess solar is available.

## Rules

### Month

Enter a month or month range. Months are numbered 1-12. To specify individual values, separate them with commas. To specify a range use a dash between the numbers. For example to enable the rule in January, February and March you could enter 1,2,3 or 1-3. The rule will only apply during these months. Leave blank for any month of the year

### Time range
Time ranges are in 24 hour format, e.g 08:00-13:00 would be 8AM to 1 PM. Leave blank for any time

### Criteria

What should trigger the rule.
1. empty. Never trigger the rule. 'Value' is ignored
1. Always. Always trigger the rule. 'Value' is ignored
1. Import price below. Trigger the rule when the import price is below the price in the 'Value' cell
1. Export price above. Trigger the rule when the import price is above the price in the 'Value' cell
1. Low rate import. Trigger the rule when the import price is below average. This is for rules where the import rate varies during the day.
1. High rate export. Trigger the rule when export price is above average. This is for rules where the import rate varies during the day.

### Function

What to do when the rule is triggered.
1. Grid priority. Any solar in excess of the load is sent to the grid. Capacity and max power are ignored.
1. Charge. Charge the battery at the max power until it reaches the given capacity.
1. Discharge. Discharge the battery at the max power until it reaches the given capacity.
1. Track load. Run the load from solar and charge/discharge the battery as needed to maintain zero grid export or import. If excess solar is available after charging the battery it is exported to grid.
1. Battery priority. Charge the battery from any available solar. Excess goes to the load and/or grid

note: Where Capacity is left blank either the battery capacity will be used for charging or zero will be used for discharging. Where max power is left blank the maximum battery charge/discharge rate will be used

### Rule priority

Rules are tested in order from top to bottom. The first rule to match the month, time and criteria will be used. If no rule matches, the inverter will default to 'track load'.

## Intelligent loads

These are loads that can be switched on when excess solar is available.

### Month

This is a range of months in the same format as is used for rules.

### Min power

The minimum power that the load can take. For loads that can be varied this is the lowest power setting. For fixed loads use the load power rating.

### Max power

The maximum power that the load can take. For loads that can be varied this is the highest power setting. For fixed loads use the load power rating.

### kWh

The total kWh needed by this load in each day. If not enough solar is available, cheap rate will be used to make up the difference.

### Min battery

In many cases you may have excess solar but not enough to run the minimum load requirement. In that case if the battery is above the min battery value (kWh), battery will be used to make up the difference. Usually this will result in the load being switched on for one half hour time slot then off for one or more time slots to allow the battery to be recharged. If left blank the battery is not used.

### Name

This is the column name for this load in the resulting CSV file. Names must be unique.

### Load priority

The highest load in the list has priority until it reaches it's kWh limit. If excess solar from the previous load is available subsequent loads will be supplied.
