from solar_utils import ToNumber, SolarException, MonthRange
from inverter import ChargeMode

class DynamicLoad:
    def __init__(self, timeScale, settings = None):
        self.minPower = 0
        self.maxPower = 0
        self.capacity = 0
        self.state = 0
        self.minBattery = 1e17
        self.month=MonthRange()
        self._timeScale = timeScale
        self.name = ""
        if settings:
            self.Load(settings)

    def GetLayout():
        import PySimpleGUI as sg
        return([sg.Frame("Intelligent loads", layout=[
            [
                sg.Text("Month", size=(13, 1)),
                sg.Text("Min power", size=(9, 1)),
                sg.Text("Max power", size=(9, 1)),
                sg.Text("kWh", size=(4, 1)),
                sg.Text("Min battery", size=(9, 1)),
                sg.Text("Name", size=(9, 1)),
            ],
            [sg.Column([
                [
                    sg.Input("", size=(12, 1), key="month"),
                    sg.Input("", size=(9, 1), key="minPower"),
                    sg.Input("", size=(9, 1), key="maxPower"),
                    sg.Input("", size=(4, 1), key="capacity"),
                    sg.Input("", size=(9, 1), key="minBattery"),
                    sg.Input("", key="name", size=(15,1)),
                ]
            ], key="loads")],
        ])])

    def Load(self, settings):
        self.month.Parse(settings['month'])
        self.minPower = ToNumber(settings['minPower'])
        self.maxPower = ToNumber(settings['maxPower'])
        self.capacity = ToNumber(settings['capacity'])
        self.minBattery = ToNumber(settings['minBattery'], 1e17)
        self.name = settings['name']
        if not self.name and self.capacity > 0:
            raise SolarException("Intelligent loads must have a name")

    def GetSchema(self):
        return([
            'month',
            'minPower',
            'maxPower',
            'capacity',
        ])

    def Run(self, month, power):
        raise SolarException("Should be overriden")

    def Reset(self):
        return


class SimDynamicLoad(DynamicLoad):
    def __init__(self, timeScale, settings = None):
        super().__init__(timeScale, settings)

    def Run(self, month, power, inverter):
        if power <= 0 or not self.month.InRange(month):
            return power , 0

        load = (self.capacity - self.state) / self._timeScale
        if load <= 0:
            return power, 0
        if power < self.minPower and power < load:
            if inverter.battery < self.minBattery:
                return power, 0
            if load > self.minPower:
                load = self.minPower
            fromBatt = load - power
            mode = inverter.chargeMode
            inverter.SetMode(ChargeMode(ChargeMode.TRACK_LOAD))
            delta = inverter.Run(0, fromBatt)
            inverter.SetMode(mode)
            rate = (load - delta)
            self.state += rate * self._timeScale
            return 0, rate
        if load > self.maxPower:
            load = self.maxPower
        if power < load:
            load = power
        self.state += load * self._timeScale
        return power - load, load

    def Reset(self):
        self.state = 0