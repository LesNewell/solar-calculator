import copy
import os
import sys
import PySimpleGUI as sg
import json
import importlib
import forms
import inputdata
import logging
import iso8601
from csvout import CsvOut, TxtOut
from datetime import datetime, timedelta, date
from inverter import SimInverter
from solar_utils import SolarException
from collections import deque
import random
from dynamicload import SimDynamicLoad

class LogHandler(logging.StreamHandler):

    def __init__(self, target):
        self._target = target
        self._buffer = ''
        logging.StreamHandler.__init__(self)

    def setTarget(self, target):
        self._target = target

    def emit(self, record):
        self._buffer += record.message + '\n'
        if self._target:
            self._target.update(value=self._buffer)
            self._target.set_vscroll_position(1)


logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    filename='solar_log.txt',
    filemode='w')

class MainWindow(forms.Form):
    def __init__(self):
        self.importCsv = inputdata.CsvFile("import", False)
        self.exportCsv = inputdata.CsvFile("export", False)
        self.usageCsv = inputdata.CsvFile("energy", True)
        self.modifierCsv = inputdata.CsvFile("modifier", True)
        self.store = {}
        self.rules = []
        self.strategy = None
        self.log = LogHandler(None)
        self.log.setLevel(logging.INFO)
        logging.getLogger('').addHandler(self.log)
        self.nstrings = 4
        self.strings = []
        self.txt=""

        dir = os.path.dirname(os.path.realpath(__file__)) + "/strategies"
        files = os.listdir(dir)
        strats = []
        for file in files:
            name = file[:-3]
            if file.endswith(".py"):
                strats.append(name)

        def GetStrings():
            ret = []
            for s in range(0, self.nstrings):
                st = str(s)
                ret.append([
                    sg.Text('String ' + st + ' data', size=(13, 1)),
                    sg.FileBrowse(file_types=(('JSON Files', '*.json'),), target='String' + st, enable_events=True),
                    sg.Button("-", size=(1, 1), key="DelButton" + st, metadata='String' + st),
                    sg.Text("Max MPPT power"),
                    sg.Input("2", key='String' + st + 'power', size=(5, 1)),
                    sg.Text('', key='String' + st),
                ])
            return ret

        layout = [
            GetStrings(),
            self.importCsv.GetLayout("Import pricing", True),
            self.exportCsv.GetLayout("Export pricing", True),
            self.usageCsv.GetLayout("         Usage", False),
            self.modifierCsv.GetLayout("Usage modifier", False),
            [sg.Text("Strategy"), sg.Combo(strats, readonly=True, key="strategy", enable_events=True),
             sg.Button("Show", key=lambda: self.ToggleStrategy())],
            [
                sg.CalendarButton("Start date", target="startDate"), sg.Input("", key="startDate"),
                sg.CalendarButton("End date", target="endDate"), sg.Input("", key="endDate")
            ],
            [sg.FileSaveAs("Output file", file_types=(("CSV Files", "*.csv"),), target="outFile"),
             sg.Text("", key="outFile")],
            [sg.FileSaveAs("Summary file", file_types=(("CSV Files", "*.csv"),), target="summaryFile"),
             sg.Text("", key="summaryFile")],
            [sg.Submit("Run", key=lambda: self.RunSim()), sg.Cancel("Exit"),
             sg.Button("Save config", key=lambda: self.Save()),
             sg.Button("Load config", key=lambda: (self.Load()))],
            [sg.Multiline("", key="log", expand_x=True, auto_refresh=True, write_only=True, size=(None, 20),
                          font="mono 8")],

        ]
        super().__init__("Solar calculator", layout, self.store)

    def ToggleStrategy(self):
        if not self.strategy or not self.strategy.form:
            return
        form = self.strategy.form
        if form.window:
            form.Close()
        else:
            form.Show()

    def StrategyChanged(self):
        strat = self.window['strategy'].get()
        if self.strategy:
            if self.strategy.form:
                self.strategy.form.Close()
            del (self.strategy)
            self.strategy = None
        dir = os.path.dirname(os.path.realpath(__file__)) + "/strategies"
        file = strat
        if os.path.exists(dir + '/' + file + '.py'):
            try:
                sys.path.append(dir)
                self.strategy = importlib.import_module(file).strategy(SimInverter(), SimDynamicLoad)
                if not strat in self.store:
                    self.store[strat] = {}
                self.strategy.form = forms.Form(strat + " strategy", self.strategy.GetLayout(), self.store[strat])
                self.strategy.name = strat
                self.strategy.form.Show()
                sys.path.pop()
            except Exception as exc:
                #                 sg.popup(exc)
                raise (exc)
            finally:
                sys.path.pop()

    def GetStore(self, name):
        if not name in self.store:
            self.store[name] = {}
        return self.store[name]

    def Load(self):
        f = sg.filedialog.askopenfile("r", filetypes=(("Config files", ".cfg"),), defaultextension=".cfg",
                                      title="Load settings")
        if not f:
            return
        try:
            self.store = json.load(f)
        except:
            sg.popup("Error reading file")
            return
        self.log.setTarget(None)
        self.SetValues(self.GetStore('main'))
        self.log.setTarget(self.window['log'])
        self.StrategyChanged()

    def Save(self):
        f = sg.filedialog.asksaveasfile("w", filetypes=(('Config files', '.cfg'),), defaultextension=".cfg",
                                        title="Save settings")
        if not f:
            return
        vals = self.GetValues()
        cwd = os.getcwd()
        cwdLen = len(cwd) + 1
        for v in vals.items():
            val = v[1]
            if isinstance(val, str) and val.startswith(cwd):
                key = v[0]
                vals[key] = val[cwdLen:]

        self.store['main'] = vals
        if self.strategy and self.strategy.form:
            self.store[self.strategy.name] = self.strategy.form.GetValues()
        json.dump(self.store, f)

    def LoadFiles(self):
        values = self._values
        nStrings = 0
        for s in range(0, self.nstrings):
            file = values['String' + str(s)]
            if file and file != "":
                if nStrings >= len(self.strings):
                    self.strings.append(inputdata.SolarFile())
                data = self.strings[nStrings]
                try:
                    data.Load(file)
                    if data.ok():
                        data.max = float(values["String" + str(s) + "power"])
                        nStrings += 1
                except inputdata.SolarException as exc:
                    sg.popup(exc)
                    return False
        if nStrings == 0:
            logging.warning("Warning: No solar data")
        for idx in range (nStrings, len(self.strings)):
            self.strings.pop(nStrings)
        try:
            self.importCsv.Load(self.window)
            self.exportCsv.Load(self.window)
            self.usageCsv.Load(self.window)
            self.modifierCsv.Load(self.window)
            self.modifierCsv.Normalise()
        except SolarException as exc:
            sg.popup(exc)
            return False
        self.txt = TxtOut()
        try:
            output = CsvOut(values['outFile'])
            self.summary = CsvOut(values['summaryFile'])
        except SolarException as exc:
            sg.popup(exc)
            return False
        return output

    def RunSim(self):
        logging.info("***** Run started *****")
        values = self.GetValues()
        if not self.strategy or not self.strategy.form:
            sg.popup("No strategy selected")
            return
        try:
            startDate = values['startDate']
            startDate = iso8601.parse_date(startDate)
            startDate = startDate.replace(hour=0, minute=0, second=0, microsecond=0)
            endDate = values['endDate']
            endDate = iso8601.parse_date(endDate)
            endDate = endDate.replace(hour=0, minute=0, second=0, microsecond=0)
        except:
            sg.popup("Invalid start or end date")
            return
        if startDate >= endDate:
            sg.popup("Start date must be before end date")
            return
        output = self.LoadFiles()
        if not output:
            return
        step = timedelta(minutes=inputdata.TimeFile.interval)
        seconds = step.total_seconds()
        hourScale = seconds / (60 * 60)
        self.hourScale = hourScale
        impTariff = deque()
        expTariff = deque()
        solarForecast = deque()
        usage = deque()
        dailyUse = 0
        solarAcc = 0
        date = startDate
        self.importCsv.Start(startDate, seconds)
        self.exportCsv.Start(startDate, seconds)
        self.usageCsv.Start(startDate, seconds)
        self.modifierCsv.Start(startDate, seconds)
        for string in self.strings:
            string.Start(startDate, seconds)
        end = date + timedelta(days=1)
        while date < end:  # initialise forecasts
            expTariff.append(self.exportCsv.Next())
            impTariff.append(self.importCsv.Next())
            tmp = self.usageCsv.Next()
            dailyUse += tmp
            usage.append(tmp)
            solar = 0
            for string in self.strings:
                val = string.Next()
                if val > string.max:
                    val = string.max
                solar += val
            solarAcc += solar
            solarForecast.append(solar)
            date += step
        date = startDate
        monthly = {}
        yearly = {}
        try:
            self.strategy.Start(self.strategy.form.GetValues(), hourScale)
        except SolarException as exc:
            sg.popup(exc)
            return


        dynLoad = 0
        for load in self.strategy.loads:
            if not load.solarOnly and load.inUsage:
                dynLoad += load.capacity / hourScale

        rowCount = 0
        m = date.month
        d = -1
        solarDaily = 0
        useScale = 1
        try:
            while date <= endDate:
                if d != date.day:
                    d = date.day
                    dist = random.gauss(0,1)
                    solarDaily = solarAcc * hourScale
                    solarDaily += (dist / 5)
                    if solarDaily < 0:
                        solarDaily = 0
                    if dailyUse > 0:
                        load = dailyUse - dynLoad
                        if load < 0.01:
                            load = 0.01
                            logging.warning("Intelligent loads exceed daily use figures. Results may be inaccurate.")
                        useScale = load / dailyUse
                    else:
                        useScale = 0
                        logging.warning("Zero daily use. Are you sure your data is correct?")

                use = usage[0] * useScale
                if self.modifierCsv.ok():
                    use *= self.modifierCsv.Next()
                row = {'Date': date, 'Import price': impTariff[0], 'Export price': expTariff[0], 'Usage': use, 'Solar': solarForecast[0]}
                self.strategy.Run(row, date, impTariff, expTariff, solarDaily)
                impTariff.popleft()
                impTariff.append(self.importCsv.Next())
                expTariff.popleft()
                expTariff.append(self.exportCsv.Next())
                dailyUse -= usage.popleft()
                tmp = self.usageCsv.Next()
                dailyUse += tmp
                usage.append(tmp)

                solar = 0
                for string in self.strings:
                    val = string.Next()
                    if val > string.max:
                        val = string.max
                    solar += val
                solarAcc += solar
                solarForecast.append(solar)
                solarAcc -= solarForecast.popleft()

                rowCount += 1
                self.AddRow(monthly, row)
                output.Write(row)
                date += step
                if m != date.month:
                    m = date.month
                    startDate = date - step
                    self.AddRow(yearly, monthly)
                    self.DoTotals(monthly, startDate.strftime("%d/%m/%Y"))

            self.AddRow(yearly, monthly)
            self.DoTotals(monthly, date.strftime("%d/%m/%Y"))
            self.DoTotals(yearly, "Year end")
            logging.info(self.txt.buffer)
        except SolarException as exc:
            sg.popup(exc)
            return
        except PermissionError as exc:
            sg.popup("File write error. Is it open in another process?")
            return
        logging.info("Output file created")
        self.summary = None

    def DoTotals(self, totals, date):
        row = copy.deepcopy(totals)
        row["Date"] = date
        row.pop('Import price')
        row.pop('Export price')
        row['Usage'] *= self.hourScale
        row['Solar'] *= self.hourScale
        self.strategy.ProcessTotals(row)
        self.txt.Write(row)
        self.summary.Write(row)
        for key in totals.keys():
            totals[key] = 0

    def AddRow(self, totals, row):
        if len(totals) == 0:
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    totals[key] = value
                else:
                    totals[key] = ""
            return
        for key, value in row.items():
            if isinstance(value, float):
                totals[key] += value

    def OnEvent(self, event, values):  # override to add event handling
        if event == "strategy":
            self.StrategyChanged()
        if event.startswith("DelButton"):
            target = self.window[event].metadata
            if target:
                self.window[target].update("")

        return

    def Run(self):
        sg.set_options(suppress_error_popups=True)
        self.Show()
        self.log.setTarget(self.window['log'])
        while self.window:
            self.Poll(20)
            if self.strategy and self.strategy.form:
                self.strategy.form.Poll()


if __name__ == '__main__':
    win = MainWindow()
    win.Run()
