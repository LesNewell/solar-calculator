from solar_utils import SolarException


class CsvOut:
    def __init__(self, fileName):
        self._f = None
        self._new = True
        try:
            self._f = open(fileName, 'w', newline='')
        except:
            raise SolarException("Unable to open " + fileName)

    def ok(self):
        return self._f is not None

    def Write(self, row):
        f = self._f
        if not f:
            return
        if self._new:
            self._new = False
            comma = ''
            for key in row:
                f.write(comma)
                f.write('"')
                f.write(key)
                f.write('"')
                comma = ','
            f.write("\r\n")
        comma = ''
        for cell in row.values():
            f.write(comma)
            if isinstance(cell, float):
                f.write('{:.2f}'.format(cell))
            elif isinstance(cell, str):
                f.write('"')
                f.write(cell)
                f.write('"')
            else:
                f.write(str(cell))
            comma = ','
        f.write("\r\n")


class TxtOut:
    def __init__(self):
        self.buffer = ""
        self._new = True
        self._widths = []

    def Write(self, row):
        if self._new:
            self._new = False
            for key, val in row.items():
                if val is None:
                    self._widths.append(0)
                    continue
                w = len(key) + 2
                self.buffer += key + "  "
                if not self._widths:
                    w += 8
                    self.buffer += "        "
                while w < 10:
                    self.buffer += ' '
                    w += 1
                self._widths.append(w)
            self.buffer += "\r\n"
        idx = 0
        acc1 = 0
        acc2 = 0
        for cell in row.values():
            w = self._widths[idx]
            idx += 1
            if w ==0:
                continue
            st = ""
            if isinstance(cell, float):
                st = '{:.2f}'.format(cell)
            else:
                st = str(cell)
            self.buffer += st
            acc1 += w
            acc2 += len(st)
            while acc2 < acc1:
                self.buffer += " "
                acc2 += 1
        self.buffer += "\r\n"