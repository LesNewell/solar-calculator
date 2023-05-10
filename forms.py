import PySimpleGUI as sg
import copy

class Form:
    def __init__(self, title, layout, values):
        if not type(values) is dict:
            raise Exception("Values must be a dictionary")
        self.title = title
        self.window = None
        self._values = values
        self._layout = layout
        self._editable = ["input", "combo", "checkbox", "radio"]
        self._pos=(None,None)


    def _AddRows(self, item, values):
        if hasattr(item, "__len__"):
            for row in item:
                self._AddRows(row, values)
            return
        if not hasattr(item, "Type"):
            return
        if not hasattr(item, "Rows"):
            return
        if item.Type != "column":
            if item.Rows:
               self._AddRows(item.Rows, values)
            return
        if not item.key:
            item.key="column"
        layout = item.Rows
        rowTemplate = copy.deepcopy(layout[0])
        nRows = 1
        vals=[]
        if item.key in self._values:
            vals = self._values[item.key]
        if not vals: #Create entries in the stored values
            row = {}
            for ctrl in rowTemplate:
                type = ctrl.Type
                if type in self._editable and ctrl.key is not None:
                    row[ctrl.key] = ""
            vals.append(row)
            self._values[item.key] = vals
        first = True
        idx = 0
        for valRow in vals:
            idxStr = item.key + str(idx) + "_"
            valRow = vals[idx]
            if first:
                row = layout[0]
                first = False
            else:
                row = copy.deepcopy(rowTemplate)
                layout.append(row)
            for itm in row:
                if itm.key:
                    itm.Key = idxStr + itm.Key
#            row.append(sg.Button('↑', key=idxStr + "up_" + item.key))
            row.append(sg.Button('↑', key=(self._MoveRow, item, idx, -1)))
            row.append(sg.Button('↓', key=(self._MoveRow, item, idx, 1)))
            row.append(sg.Button('+', key=(self._AddRow, item, idx)))
            row.append(sg.Button('-', key=(self._RemoveRow, item, idx, -1)))
            idx += 1


    def _GetKey(self, item):
        try:
            i = item.key.index('_')
            return item.key[i + 1:]
        except:
            return None

    def _GetIndex(self, item):
        try:
            i = item.key.index('_')
            return int(item.key[:i + 1])
        except:
            return None

    def _MoveRow(self, params):
        item = params[1]
        idx = params[2]
        dir = params[3]
        toIdx = idx + dir
        layout = item.Rows
        if toIdx < 0 or toIdx >= len(layout):
            return
        row1 = layout[idx]
        row2 = layout[toIdx]
        for idx in range(0,len(row1)):
            item1 = row1[idx]
            if not item1.Type in self._editable:
                continue
            item2 = row2[idx]
            tmp = item1.get()
            item1.update(item2.get())
            item2.update(tmp)

    def _RemoveRow(self, params):
        item = params[1]
        idx = params[2]
        values = self.GetValues()[item.key]
        if not values:
            return
        if len(values) < 2:
            self._values[item.key]=[]
        else:
            del values[idx]
        self.Show()

    def _AddRow(self, params):
        item = params[1]
        idx = params[2]
        values = self.GetValues()[item.key]
        if not values:
            return
        row = copy.deepcopy(values[idx])
        for key in row.keys():
            row[key] = ""
        values.insert(idx + 1, row)
        self.Show()

    def _ShowValues(self, layout, values):
        for item in layout:
            if type(item) is list:
                self._ShowValues(item, values)
                continue
            if item.Type == "column":
                if item.key in values:
                    vals = values[item.key]
                    idx = 0
                    for row in item.Rows:
                        for itm in row:
                            if itm.Type in self._editable and itm.key:
                                key = self._GetKey(itm)
                                if key and key in vals[idx]:
                                    itm.update(vals[idx][key])
                        idx +=1
                    self._ShowValues(item.Rows, values[item.key])
                    continue
            if item.Type == "button":
                if item.Target:
                    try:
                        item = self.window.find_element(item.Target, True)
                        if item and item.Type == "text" and item.key in values:
                            item.update(values[item.key])
                    except:
                        continue
                continue
            if item.Type in self._editable:
                if item.key in values:
                    item.update(values[item.key])
                continue
            if hasattr(item, "Rows"):
                self._ShowValues(item.Rows, values)

    def _GetValues(self, values, layout):
        for item in layout:
            if type(item) is list:
                self._GetValues(values, item)
                continue
            if item.Type == "column" and item.key:
                values[item.key] = []
                for row in item.Rows:
                    r = {}
                    for itm in row:
                        if itm.Type in self._editable and itm.key:
                            key = self._GetKey(itm)
                            if key:
                                r[key] = itm.get()
                    values[item.key].append(r)
                continue
            if hasattr(item, "Rows"):
                self._GetValues(values, item.Rows)
                continue
            if item.Type == "button":
                if item.Target:
                    try:
                        item = self.window.find_element(item.Target, True)
                        if item and item.Type == "text":
                            values[item.key] = item.get()
                    except:
                        continue
                continue
            if item.Type in self._editable and item.key:
                values[item.key] = item.get()


    def GetValues(self):
        if not self.window:
            return self._values
        ret = {}
        self._GetValues(ret, self.window.Rows)
        self._values = ret
        return ret

    def SetValues(self, values):
        if not type(values) is dict:
            raise Exception("Values must be a dictionary")
        self._values = values
        if self.window:
            self.window.close()
            self.window = None
            self.Show()


    def Show(self):
        if self.window:
            self._pos = self.window.current_location(more_accurate = True)
            self.window.close()
            self.window = None
        layout = copy.deepcopy(self._layout)
        self._AddRows(layout, self._values)
        self.window = sg.Window(self.title, layout, finalize = True, location=self._pos, enable_close_attempted_event=True)
        self._ShowValues(layout, self._values)

    def Close(self):
        if not self.window:
            return
        pos = self.window.current_location(more_accurate=True)
        if pos[0] is not None:
            self._pos = pos
        self.GetValues()
        self.window.close()
        self.window = None

    def Poll(self, timeout = 0):
        if not self.window:
            return
        event, values = self.window.read(timeout = timeout)
        if event == sg.TIMEOUT_EVENT:
            return
        if type(event) is tuple and callable(event[0]):
            event[0](event)
            return
        if event == sg.WIN_CLOSE_ATTEMPTED_EVENT or event == 'Exit':
            self.Close()
        elif callable(event):
            event()
        else:
            self.OnEvent(event, values)

    def Run(self):
        if not self.window:
            self.Show()
        while self.window:
            self.Poll()

    def OnEvent(self, event, values): #override to add event handling
        return

