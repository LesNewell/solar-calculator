from inverter import Inverter, ChargeMode
from solar_utils import ToNumber, SolarException, TimeRange, MonthRange
from dynamicload import DynamicLoad

class Rule:
    ALWAYS = "Always"
    IMPORT_BELOW = "Import price below"
    EXPORT_ABOVE = "Export price above"
    LOW_IMPORT = "Low rate import"
    HIGH_EXPORT = "High rate export"


    def __init__(self, parent, settings = None):
        self.parent = parent
        self.month = MonthRange()
        self.time = TimeRange(parent.timeScale)
        self._criteria = None
        self.value = None
        self.limit = None
        self.rate = None
        self._function = None
        self.funcArg = 0
        if settings:
            self.Load(settings)

    def GetLayout():
        import PySimpleGUI as sg
        ruleNames=[
            '',
            Rule.ALWAYS,
            Rule.IMPORT_BELOW,
            Rule.EXPORT_ABOVE,
            Rule.LOW_IMPORT,
            Rule.HIGH_EXPORT,
        ]
        return ([
            sg.Frame("Rules", layout=[
                [
                    sg.Text("Month", size=(13, 1)),
                    sg.Text("Time range", size=(13, 1)),
                    sg.Text("Criteria", size=(18, 1)),
                    sg.Text("Value", size=(7, 1)),
                    sg.Text("Function", size=(13, 1)),
                    sg.Text("Capacity", size=(7, 1)),
                    sg.Text("Max power", size=(9, 1))
                ],
                [sg.Column([
                    [
                        sg.Input("", size=(12, 1), key= "month"),
                        sg.Input("", size=(12, 1), key= "time"),
                        sg.Combo(ruleNames, size=(17,1), readonly=True, key= "rule"),
                        sg.Input("", size=(6, 1), key= "ruleValue"),
                        sg.Combo(ChargeMode.names, size=(12, 1), readonly=True, key= "mode"),
                        sg.Input("", size=(6, 1), key = "limit"),
                        sg.Text("at", size=(2,1)),
                        sg.Input("", size=(6, 1), key="rate"),
                    ]
                ], key='rules')],
            ])
        ])

    def _ParseFunc(self, mode):
        self._function = None
        cmds=[]
        idx = 0
        for name in ChargeMode.names:
            cmds.append([name, self._SetMode, idx])
            idx += 1

        for cmd in cmds:
            if cmd[0] == mode:
                self._function = cmd[1]
                self.funcArg = cmd[2]
                return
        if mode:
            raise SolarException("Function '" + mode + "' is not implemented")


    def _ParseRule(self, rule):
        cmds=[
            ['', None],
            [Rule.ALWAYS, self._FuncAlways],
            [Rule.IMPORT_BELOW, self._CritImpBelow],
            [Rule.EXPORT_ABOVE, self._CritExpAbove],
            [Rule.LOW_IMPORT, self._CritLowImp],
            [Rule.HIGH_EXPORT, self._CritHighExp],
        ]
        for cmd in cmds:
            if cmd[0] == rule:
                self._criteria = cmd[1]
                return
        raise SolarException("Rule '" + rule + "' is not implemented")
    def Load(self, settings):
        self._criteria = None
        self.month.Parse(settings['month'])
        self.time.Parse(settings['time'])
        self._ParseRule(settings['rule'])
        self.value = ToNumber(settings['ruleValue'], None)
        self.limit = ToNumber(settings['limit'], None)
        self.rate = ToNumber(settings['rate'], 1e17)
        self._ParseFunc(settings['mode'])

    def _FuncAlways(self, row):
        return 0

    def _CritImpBelow(self, row):
        if not self.value:
            raise SolarException("Rule value must be specified")
        if self.value < row['Import price']:
            return 0
        else:
            return None

    def _CritExpAbove(self, row):
        if not self.value:
            raise SolarException("Rule value must be specified")
        if self.value > row['Import price']:
            return 0
        else:
            return None

    def _CritLowImp(self, row):
        rates = self.parent.impRates
        if not rates:
            return None
        ct = 0
        for idx in range(self.parent.impIdx, len(rates)):
            rate = rates[idx]
            if rate >= 0:
                break
            ct += 1
        if ct == 0:
            return None
        return ct * self.parent.timeScale

    def _CritHighExp(self, row):
        rates = self.parent.expRates
        if not rates:
            return None
        ct = 0
        for idx in range(self.parent.expIdx, len(rates)):
            rate = rates[idx]
            if rate <= 0:
                break
            ct += 1
        if ct == 0:
            return None
        return ct * self.parent.timeScale


    def _SetMode(self, row, remaining):
        mode = self.parent.chargeMode
        mode.mode = self.funcArg
        mode.rate = self.rate
        mode.limit = self.limit
        if mode.mode == ChargeMode.DISCHARGE:  # special case
            lim = self.limit
            if lim is None:
                self.limit = 0
                lim = 0
            lim = self.parent.inverter.battery - lim
            if lim > 0:  # reduce discharge to spread it over remaining time
                lim /= remaining
                mode.limit = lim
        return True

    def Run(self, row, month, hour):
        if not self.month.InRange(month) or self._criteria is None or not self._function:
            return False
        rem1 = self._criteria(row)
        if rem1 is None:
            return False
        remaining = self.time.Remaining(hour)
        if remaining is None:
            return False
        if rem1 > remaining:
            remaining = rem1
        return self._function(row, remaining)


class strategy:
    def __init__(self, inverter, loadType):
        self.loadType = loadType
        self.inverter = inverter
        self.rules=[]
        self.timeScale = 1
        self.form = None
        self.loads=[]
        self.day = -1
        self.chargeMode = ChargeMode()
        self.impRates = []
        self.expRates = []
        self.impIdx = 0
        self.expIdx = 0
        self.loadReset = 0

    def GetLayout(self):
        layout = [
            Inverter.GetLayout(),
            Rule.GetLayout(),
            DynamicLoad.GetLayout(),
        ]
        return layout

    def Start(self, settings, timeScale):
        self.timeScale = timeScale
        self.inverter.Start(settings, timeScale)
        self.rules=[]
        for rule in settings['rules']:
            self.rules.append(Rule(self, rule))
        self.loads = []
        for load in settings['loads']:
            self.loads.append(self.loadType(timeScale, load))
        self.day = -1

    def CalcRates(self, forecast):
        if len(forecast) < 1:
            return([0])
        avg = 0
        min = 1e17
        max = -1e17
        for step in forecast:
            avg += step
            if step < min:
                min = step
            if step > max:
                max = step
        avg /= len(forecast)
        ret = []
        peak = max
        min += (avg-min) / 3
        max += (avg-max) / 3
        if min > avg:
            min = avg
        if max < avg:
            max = avg
        minHours = 3 / self.timeScale
        hourCount = 0

        if max - min < 0.01: # Fixed rate so just do 8pm to 4am 'cheap'
            count = int(24/self.timeScale)
            p1 = 4 / self.timeScale
            p2 = 20 / self.timeScale
            for i in range(0, count):
                if i <= p1 or i > p2:
                    ret.append(-1)
                else:
                    ret.append(0)
            return ret

        for step in forecast:
            if step < min:
                ret.append(-1)
                hourCount += 1
            elif step > max:
                ret.append(1)
            else:
                ret.append(0)
        iterations = 0
        peak += 0.001
        while hourCount < minHours: #must have at least minHours of cheap rates
            iterations += 1
            min2 = min
            min += (peak-min2) / 5
            hourCount = 0
            idx = 0
            for idx in range(0, len(ret)):
                step = forecast[idx]
                if step <= min:
                    ret[idx] = -1
                    hourCount += 1
        print (iterations)
        return ret
    # impForecast and expForecast are deques containing future pricing for the next 24 hours in 30 minute increments.
    # The first item is in the next 30 minutes and so on.
    # solarForecast is a prediction of tomorrow's total solar generation in kWh with a randomised amount of error
    def Run(self, row, date, impForecast, expForecast, solarForecast):
        imp = row['Import price']
        exp = row['Export price']
        month = date.month
        hour = date.hour + (date.minute / 60)
        day = date.day
        if day != self.day:
            self.day = day
            self.impRates = self.CalcRates(impForecast)
            self.expRates = self.CalcRates(expForecast)
            self.impIdx = 0
            self.expIdx = 0
            self.loadReset = 0
        else:
            self.impIdx += 1
            if self.impIdx >= len(self.impRates):
                self.impIdx = len(self.impRates)
            self.expIdx += 1
            if self.expIdx >= len(self.expRates):
                self.expIdx = len(self.expRates)
        self.chargeMode.mode = None
        batt = self.inverter.battery
        for rule in self.rules:
            if not rule.Run(row, month, hour):
                continue
        if self.chargeMode.mode is None:
            if self.inverter.chargeMode != ChargeMode.DEFAULT:
                self.inverter.SetMode(ChargeMode())
        else:
            self.inverter.SetMode(self.chargeMode)

        power = self.inverter.Run(row['Solar'], row['Usage'])

        if self.impRates[self.impIdx] < 0: #running in cheap rate
            if self.loadReset == 0:
                self.loadReset = 1
            p = 20 #20kW max load
            for load in self.loads:
                rate = 0
                if p > 0 and not load.solarOnly:
                    p, rate=load.Run(month, hour, p, self.inverter)
                if load.name:
                    row[load.name] = rate
            power += p - 20
        else:
            if self.loadReset == 1:
                for load in self.loads:
                    load.Reset()
                self.loadReset = 2
            solar = row['Solar']
            for load in self.loads:
                rate = 0
                if power > 0 and solar > 0:
                    power, rate = load.Run(month, hour, power, self.inverter)
                if load.name:
                    row[load.name] = rate

        imported = 0
        exported = 0
        if power > 0:
            exported = power
        else:
            imported = -power
        row['Imported'] = imported
        row['Import cost'] = imported * row['Import price'] * self.timeScale
        row['Exported'] = exported
        row['Export profit'] = exported * row['Export price'] * self.timeScale
        if self.inverter.capacity > 0:
            chargeRate = self.inverter.battery - batt
            if chargeRate > 0:
                chargeRate /= self.inverter.battEfficency
            row['Charge rate'] = chargeRate  / self.timeScale
            row['Battery'] = self.inverter.battery
            row['Battery cycles'] = abs(chargeRate) / ( 2 * self.inverter.capacity)
        bill = row['Import cost'] - row['Export profit']
        row['Bill'] = bill

    def ProcessTotals(self, row):
        row['Imported'] *= self.timeScale
        row['Exported'] *= self.timeScale
        if 'Charge rate' in row:
            row.pop('Charge rate')
            row.pop('Battery')
        for load in self.loads:
            if load.name:
                row[load.name] *= self.timeScale
