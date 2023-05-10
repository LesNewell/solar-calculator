from solar_utils import ToNumber, SolarException


class ChargeMode:
    GRID = 0
    CHARGE = 1
    DISCHARGE = 2
    TRACK_LOAD = 3
    TRACK_SOLAR = 4

    DEFAULT=TRACK_LOAD

    names=[
        "Grid priority",
        "Charge",
        "Discharge",
        "Track load",
        "Battery priority"
    ]

    def __init__(self, mode = None):
        if not mode:
            mode = ChargeMode.DEFAULT
        self.mode = mode
        self.limit = None
        self.rate = 1000000

    def SetMode(self, name):
        try:
             self.mode = ChargeMode.names.index(name)
        except:
            raise SolarException("Unknown charge mode :", name)

    def SetLimit(self, limit):
        self.limit = ToNumber(limit, None)

    def SetRate(self, rate):
        self.rate = ToNumber(rate, 1000000)

class Inverter:
    def __init__(self):
        self.battery = 0
        self.capacity = 0
        self._charge = 0
        self._discharge = 0
        self.chargeMode = ChargeMode()


    def GetLayout():
        import PySimpleGUI as sg
        return ([
            [
                sg.Text("Battery usable capacity (kWh)"),
                sg.Input("0", key="capacity", size=(5, 1)),
                #                sg.Text("Cycle life (cycles)"),
                #                sg.Input("4000", key="cycles", size=(5, 1)),
                #                sg.Text("Cost"),
                #                sg.Input("3000", key="batCost", size=(5, 1)),
            ],
            [
                sg.Text("Max charge rate (kW)"),
                sg.Input("0", key="charge", size=(5, 1)),
                sg.Text("Max discharge rate (kW)"),
                sg.Input("0", key="discharge", size=(5, 1)),
            ],
            [
                sg.Text("Max inverter output (kW)"),
                sg.Input("0", key="output", size=(5, 1)),
            ],
        ])


class SimInverter(Inverter):

    def __init__(self):
        self.efficiency = 0.95
        self.battEfficency = 0.9
        self._output = 0
        self._timeScale = 1
        # Simulates charge rate reduction as the battery reaches full charge
        # Increasing the value slows down charging more
        self.filter = 0.8
        super().__init__()

    def Start(self, settings, timeScale):
        self._timeScale = timeScale
        self.capacity = ToNumber(settings['capacity'])
        self._charge = ToNumber(settings['charge'])
        self._discharge = -ToNumber(settings['discharge'])
        self._charge = ToNumber(settings['charge'])
        self._output = ToNumber((settings['output']))
        self.chargeMode = ChargeMode()
        self.battery = 0

    def SetMode(self, mode):
        self.chargeMode = mode

    # returns grid power, +ve = export
    def Run(self, solar, load):
        solar *= self.efficiency
        export = solar - load #+ve value = spare to export/charge
        charge = self.chargeMode
        rate = 0
        if charge.mode== ChargeMode.GRID:  #Only charge if we have more solar than we can export
            if export > self._output:
                rate = export - self._output
        elif charge.mode == ChargeMode.CHARGE or charge.mode == ChargeMode.TRACK_SOLAR:
            if charge.mode == ChargeMode.TRACK_SOLAR:
                rate = export
                if rate < 0:
                    rate = 0
            else:
                rate = self.chargeMode.rate
                if rate < export:
                    rate = export
            limit = charge.limit
            if limit is None or limit > self.capacity:
                limit = self.capacity
            batt = (limit - self.battery) / (self._timeScale * self.battEfficency)
            if batt < limit:
                limit = batt
                if limit < 0:
                    limit = 0
            if rate > limit:
                rate = limit
        elif charge.mode == ChargeMode.TRACK_LOAD:
            rate = export
        elif charge.mode == ChargeMode.DISCHARGE:
            rate = self.chargeMode.rate
            limit = charge.limit
            if limit is None or limit > -self._discharge:
                limit = -self._discharge
            batt = self.battery / self._timeScale
            if batt < limit:
                limit = batt
            if rate > limit:
                rate = limit
            if rate > self._output - export:
                rate = self._output - export
            rate = -rate

        rate = self._DoCharge(rate)
        export -= rate
        if export > self._output:
            export = self._output
        return export

    def _DoCharge(self, rate):
        if rate > 0:
            maxRate = ((self.capacity - self.battery) * self.filter) / self._timeScale
            if rate > maxRate:
                rate = maxRate
                if rate < 0:
                    rate = 0
            if rate > self._charge:
                rate = self._charge
            self.battery += rate * self.battEfficency * self._timeScale
        elif rate < 0:
            maxRate = -self.battery / self._timeScale
            if rate < maxRate:
                rate = maxRate
                if rate > 0:
                    rate = 0
            if rate < self._discharge:
                rate = self._discharge
            self.battery += rate * self._timeScale
        return rate



