import logging as log

def ToNumber(value, default = 0):
    try:
        return float(value)
    except:
        if value:
            log.error("Unable to convert '" + value + "' to a number")
        return default



class TimeRange:
    def __init__(self, default, string = None):
        self._ranges=[]
        self._default = default
        self.Parse(string)

    def _ToTime(self, s):
        chunks = s.split(":")
        if len(chunks) != 2:
            raise SolarException("Invalid time range")
        try:
            hour = int(chunks[0])
            minute = int(chunks[1])
            return hour + (minute / 60)
        except:
            raise SolarException("Invalid time range")

    def Remaining(self, hour):
        if not self._ranges:
            return self._default
        for r in self._ranges:
            if hour >= r[0] and hour < r[1]:
                return r[1] - hour
        return None

    def Parse(self, string):
        self._ranges=[]
        if not string:
            return
        cur = ""
        prev = None
        for c in string:
            if c == "-":
                if prev:
                    raise SolarException("Unexpected '-' in time range")
                prev = cur
                cur = ""
            elif c == ",":
                if not prev or not cur:
                    raise SolarException("Unexpected , in time range")
                _ranges.append([self._ToTime(prev), self._ToTime(cur)])
                prev = None
                cur = ""
            else:
                cur += c
        if prev or cur:
            if not prev or not cur:
                raise SolarException("Unexpected , in time range")
            self._ranges.append([self._ToTime(prev), self._ToTime(cur)])


class MonthRange:
    def __int__(self, string = None):
        _states = [True] * 13
        self.Parse(string)

    def InRange(self, month):
        if(month <= 0 or month > 12):
            return False
        return self._states[month]

    def _AddRange(self, start, end):
        if (start and (start < 1 or start > 12)) or end < 1 or end > 12:
            raise SolarException("Month out of range")
        if start:
            if start > end:
                raise SolarException("Invalid month range")
            for n in range(start, end + 1):
                self._states[n] = True
        else:
            self._states[end] = True

    def Parse(self, string):
        if not string:
            self._states=[True] * 13
            return
        self._states = [False] * 13
        num = 0
        prev = None
        for c in string:
            n = ord(c)
            if 48 <= n < 58:
                num *= 10
                num += n - 48
            elif c == "-":
                if prev:
                    raise SolarException("Unexpected '-' in month range")
                prev = num
                num = 0
            elif c == ",":
                self._AddRange(prev, num)
                num = 0
                prev = None
            elif c != " ":
                raise SolarException("Unknown character in month range")
        self._AddRange(prev, num)

class SolarException(Exception):
    def __init__(self, message):
        self.message = message
        log.error(message)
        super().__init__(self.message)