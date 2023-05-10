import time
import copy
import PySimpleGUI as sg
import csv
import iso8601
from datetime import datetime,timedelta, date
import forms
from enum import IntEnum
import re
import json
import logging
import os
from solar_utils import SolarException

class TimeFile():
    DATETIME = -1
    UNKNOWN = 0
    DAY = 1
    WEEK = 7
    YEAR = 365
    ABSOLUTE = 4
    interval = 30 #Number of minutes between each iteration
    multiplier = 0.5

    def __init__(self, energy = False):
        self.data=[]
        self.type = TimeFile.UNKNOWN
        self.energy = energy
        self._file = ""
        self._index = 0
        self._span = 0
        self._modified = 0
        TimeFile.multiplier = TimeFile.interval / 60
        self._increment = 30*60

    def ok(self):
        return(len(self.data) >= 2 and self.type > TimeFile.UNKNOWN)

    def Normalise(self):
        total = 0
        for row in self.data:
            total += row[1]
        total /= self._span / (60*60)
        for row in self.data:
            row[1] /= total


    def _ConvertToPower(self):
        src = self.data
        if self.type == TimeFile.ABSOLUTE:
            raise SolarException("Not yet handled")
        span = self._span

#        idx = 0
#        count = min(20,len(src) - 1)
#        prev = src[0][0]
#        avg = timedelta()
#        for idx in range(1, count)
#            cur = src[idx][0]
#            avg += cur - prev
#            prev = cur
#        avg /= count
        hour = 60 * 60
        if src[0][0] < TimeFile.interval:  # values are at the start of each interval
            src[0][0] = 0
            prev = src[0]
            for idx in range(1, len(src)):
                cur = src[idx]
                hours = (cur[0] - prev[0]) / hour
                prev[1] /= hours
                prev = cur
            hours = (span - prev[0]) / hour
            prev[1] /= hours
        else:
            raise SolarException("TDOD: handle values at end of interval")
            last = src[len(src) -1][0]
            endHours = (span - last) / hour
            prev = timedelta()
            last = None
            for row in src:
                hours = (row[0] - prev) / hour
                if endHours:
                    hours += endHours
                    row[1] /= hours
                    last = [span, row[1]]
                    endHours = 0
                else:
                    row[1] /= hours
            if last:
                src.append(last)


    def Start(self, date, increment):
        date = date.replace(tzinfo = None)
        self._increment = increment
        if self.type <= TimeFile.UNKNOWN:
            raise SolarException("File not loaded?")
        if self.type == TimeFile.ABSOLUTE:
            index = date - self._start
        elif self.type == TimeFile.DAY:
            index = timedelta(hours = date.hour, minutes = date.minute)
        elif self.type == TimeFile.WEEK:
            index = timedelta(days = date.weekday, hours = date.hour, minutes = date.minute)
        elif self.type == TimeFile.YEAR:
            index = timedelta(days = date.day, hours = date.hour, minutes = date.minute)
        self._position = index.total_seconds()
        self._index = 0

    def ShowDates(self, date):
        index = self._index
        self._index = 0
        increment = self._increment
        self._increment = 0
        self.Next()
        self._increment = increment
        self._index = index
        logging.info("Requested start date " + str(date) + " using " + str(self.data[self._index][2]) + " in " + self._file)

    def Next(self):
        self._position += self._increment
        while self._position > self._span:
            self._position -= self._span
            self._index = 0
        cur = self._index
        next = cur + 1
        while next < len(self.data) and self.data[next][0] < self._position:
            cur += 1
            next += 1
        self._index = cur
        row = self.data[cur]
        return row[1]

    def _FindType(self):
        if len(self.data) < 2:
            return TimeFile.UNKNOWN
        if self.type > TimeFile.UNKNOWN:
            return self.type
        self._span = 0
        delta = self.data[len(self.data) - 1][2] - self.data[0][2]
        step = delta / (len(self.data) - 1)
        delta += step
        days = delta.total_seconds() / (60 * 60 * 24)
        ret = TimeFile.UNKNOWN
        start = self.data[0][2]
        start = start.replace(microsecond = 0, second = 0, minute = 0)
        logging.info("Range available " + str(start) + " - " + str(self.data[len(self.data) - 1][2] ))

        if days <= 1:
            delta = timedelta(days = 1)
            ret = TimeFile.DAY
            start = start.replace(hour = 0)
        elif days > 6.5 and days < 7.5:
            delta = timedelta(days = 7)
            ret = TimeFile.WEEK
            start = start.replace(hour = 0)
        elif days > 350 and days < 380:
            delta = timedelta(days = 365)
            start = datetime(start.year, 1, 1)
            ret = TimeFile.YEAR
        else:
            start = self.data[0][2]
            self._start = start
            ret = TimeFile.ABSOLUTE
        self._span = delta.total_seconds()
        src = self.data
        dest = []
        end = start + delta
        wrap = len(src) -1
        while wrap >=0: #find wrap point
            row = src[wrap]
            if row[2] < end:
                break
            wrap -= 1
        wrap += 1
        for idx in range(wrap, len(src)):
            row = src[idx]
            row[0] = (row[2] - (start + delta)).total_seconds()
            dest.append(row)

        for idx in range(0, wrap):
            row = src[idx]
            row[0] = (row[2] - start).total_seconds()
            dest.append(row)
        self.data = dest
        self.type = ret
        return ret

    def _OpenFile(self, fName):
        if not fName:
            raise SolarException("Need to select a file for " + self._caption)
        if not os.path.exists(fName):
            raise SolarException("File does not exist:" + fName)
        if fName == self._file and self.ok() and os.path.getmtime(fName) == self._modified:
            logging.info("Using cached file " + fName)
            return False
        logging.info("Loading " + fName)
        f = open(fName)
        if not f:
            raise SolarException("Could not open " + fName)
        return f

    def Get(self, date):
        target = copy(date)
        if self.type == TimeFile.DAY:
            target = target.replace(year = 0, month = 0, day = 0)
        elif self.type == TimeFile.WEEK:
            target = target.replace(year = 0, month = 0, day = date.weekday())
        elif self.type == TimeFile.YEAR:
            target = target.replace(year = 0)

        idx = self._index
        if target < self.data[idx][0]:
            idx -= 1
            while idx > 0 and target < self.data[idx][0]:
                idx -= 1
            if idx < 0:
                idx = 0
        else:
            idx += 1
            while idx < len(self.data) and target > self.data[idx][0]:
                idx += 1
            idx -= 1
        self._index = idx
        return self.data[idx][1]


class CsvFile(TimeFile):
    def __init__(self, title, energy = False):
        self._title = title
        self._caption = ""
        super().__init__(energy)

    def GetLayout(self, caption, multipler):
        self._caption = caption
        layout = [
            sg.Text(caption, size=(13,1)),
            sg.FileBrowse(file_types=(("CSV Files", "*.csv"),), target=self._title + "-file"),
            sg.Button("-", size=(1, 1), key="DelButton", metadata=self._title + "-file"),
            sg.Text("Date/time column"),
            sg.Input(key=self._title + "-date", size=[12, 1]),
            sg.Text("Value column"),
            sg.Input(key=self._title + '-value', size=[12, 1])
        ]
        if multipler:
            layout.append(sg.Checkbox("divide by 100", key=self._title + "-div100"))
        layout.append(sg.Text("", key=self._title + "-file"))
        return layout


    def _GetColIndexes(self, row, dateHdr, valueHdr):
        dateCol = -1
        valueCol = -1
        if dateHdr.isnumeric():
            dateCol = int(dateHdr)
            if dateCol < 0 or dateCol >= len(row):
                raise SolarException("Date column is out of range" + self._errfile)
            dateHdr = False
        else:
            dateHdr = dateHdr.lower()
        if valueHdr.isnumeric():
            valueCol = int(valueHdr)
            if valueCol < 0 or valueCol >= len(row):
                raise SolarException("Value column is out of range" + self._errfile)
            valueHdr = False
        else:
            valueHdr = valueHdr.lower()

        if (dateCol == valueCol) and dateCol != -1:
            raise SolarException("Date and value columns cannot be the same")
        if dateCol >= 0 and valueCol >= 0:
            return dateCol, valueCol, False
        idx = -1;
        skip = False
        for cell in row:
            idx += 1
            cell = cell.lower()
            if dateHdr and cell == dateHdr:
                dateCol = idx
                skip = True
            if valueHdr and cell == valueHdr:
                valueCol = idx
                skip = True
        if valueCol < 0:
            raise SolarException("Unable to find value colum" + self._errfile)
        if dateCol < 0:
            raise SolarException("Unable to find date column" + self._errfile)
        return dateCol, valueCol, skip

    def _ToDate(self, value):
        match = re.match("^(?:[01]?\d|2[0-3])(?::[0-5]\d){1,2}$", value)
        ret = 0
        type = 0
        if match:  # is a time
            type = TimeFile.DAY
            hms = value.split(':')
            h = 0
            m = 0
            s = 0
            l = len(hms)
            h = int(hms[0])
            if l > 1:
                m = int(hms[1])
            if l > 2:
                s = int(hms[2])
            ret = datetime.now().replace(hour=h, minute=m, second=s, microsecond = 0)
        else:
            try:
                ret = iso8601.parse_date(value)
                ret = datetime(ret.year, ret.month, ret.day, ret.hour, ret.minute )
                type = TimeFile.DATETIME
            except:
                raise SolarException("Unable to parse date '" + value + "'" + self._errfile)
        if not self.type:
            self.type = type
        elif self.type != type:
            raise SolarException("Mismatched date/time values" + self._errfile)
        return ret

    def Load(self, window):
        fName = window[self._title + "-file"].get()
        f = self._OpenFile(fName)
        if not f:
            return
        self.data = []
        self.type = TimeFile.UNKNOWN
        self._file = ""
        self._span = timedelta()
        dateHdr = window[self._title + "-date"].get()
        valHdr = window[self._title + "-value"].get()
        values = []
        data = csv.reader(f)
        if not data:
            raise SolarException("Could not open " + fName)
        self._file = fName
        self._errfile = " in file " + fName
        self._modified = os.path.getmtime(fName)
        dateCol = -1
        valueCol = -1
        rowSize = 0
        mult = 1
        item = window.find_element(self._title + "-div100", silent_on_error = True)
        if item.Type == "checkbox" and item.get():
            mult = 0.01
        try:
            for row in data:
                if valueCol < 0:
                    dateCol, valueCol, skip = self._GetColIndexes(row, dateHdr, valHdr)
                    if rowSize < dateCol:
                        rowSize = dateCol
                    if rowSize < valueCol:
                        rowSize = valueCol
                    if skip:
                        continue
                if len(row) <= rowSize:
                    logging.info("Skipped under size row in " + fName)
                    continue
                dat = [0, 0, 0]
                if dateCol >= 0:
                    dat[2] = self._ToDate(row[dateCol])
                try:
                    dat[1] = float(row[valueCol]) * mult
                except:
                    raise SolarException("Unable to parse value '" + row[valueCol] + "'" + self._errfile)
                values.append(dat)
        except PermissionError as exc:
            raise SolarException(fName + " is locked by another process")
            return
        if len(values) < 2:
            raise SolarException("Not enough lines" + self._errfile)
        self.data = values
        self.type = TimeFile.UNKNOWN
        self._FindType()
        if self.energy:
            self._ConvertToPower()

class SolarFile(TimeFile):
    def __init__(self):
        super().__init__(False)

    def Load(self, fileName):
        if not fileName:
            return False
        f = self._OpenFile(fileName)
        if not f:
            return
        self.data = []
        self.type = TimeFile.UNKNOWN
        self._file = ""
        self._span = timedelta()
        self._file = fileName
        self._errfile = " in file " + fileName
        self._modified = os.path.getmtime(fileName)
        data = json.load(f)
        if not "inputs" in data or not "outputs" in data:
            raise SolarException("PVGIS data not found" + self._errfile)
        inputs = data['inputs']
        if not "pv_module" in inputs or not "peak_power" in inputs['pv_module'] or inputs['pv_module']['peak_power'] <= 0:
            raise SolarException("No PV data" + self._errfile + " Did you turn on PV power before generating data?")
        if not "hourly" in data['outputs']:
            raise SolarException("Hourly data not found" + self._errfile + " Make sure you select 'Hourly data' as your data set.")
        hourly = data['outputs']['hourly']
        self._energy = False
        dat = self.data
        for x in hourly:
            time = x['time']
            year =  int(time[0:4])
            month = int(time[4:6])
            day = int(time[6:8])
            hour = int(time[9:11])
            min = int(time[11:13])
            time = datetime(year, month,day,hour,min)
            dat.append([0, x['P']/1000, time])
        self._FindType()
        return True