from collections import namedtuple
import numpy as np

from .vp_utils import *


# holds parameter information and allows setting of parameters
class _Params:
    def __init__(self, inst):
        self.ws = inst.ws
        self.names = []
        params = inst.ws.cdf.get_inst_CDF(inst.inst).parameters
        if params is not None:
            for x in params:
                param_name = x.name.replace("?", "")
                self.names.append(param_name)
                setattr(self, param_name, x)

    def __setitem__(self, key, value):
        getattr(self, key).value = value

    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        return internal_iter(self, self.names)


class _Pin:
    def __init__(self, fname, name, pos , x, y, netname):
        self.fname = fname
        self.name = name
        self.pos = pos
        self.x = x
        self.y = y
        self.netname = netname

# Pin = namedtuple('Pin', 'x y')


# Holds pin information for an instance
class _Pins:
    def __init__(self, inst):

        pl = inst.ws.sch.symbol_to_pin_list(inst.inst.lib_name,
                                            inst.inst.cell_name, "symbol")

        self.names = [x["name"] for x in pl["ports"]]

        for x in pl["ports"]:
            bbox = x["pins"][0]["fig"]["bBox"]
            # get pos from virtuoso coords
            pos = calc_center(bbox)
            pos = np.asarray(pos)

            if inst.mirrored == 'Y':
                pos[0] = -pos[0]
            elif inst.mirrored == 'X':
                pos[1] = -pos[1]

            pos = [pos[0] + inst.vpos[0], pos[1] + inst.vpos[1]]

            pos = rotate(pos, inst.vpos, inst.rot)

            # transform out of virtuoso coords
            pos = i_transform(pos)
            full_name = f"/{inst.name}/{x['name']}"
            p = _Pin(full_name, x["name"], pos, pos[0], pos[1], None)
            # p = Pin(pos[0], pos[1])
            setattr(self, x["name"], p)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except:
            raise(Exception(f"Error: pin '{key}' does not exist. Available pins: {self.names}"))

    def __iter__(self):
        return internal_iter(self, self.names)


# Allows creation and manipulation of a symbol in a schematic
class _Inst:
    def __init__(self, ws, cv, lib_name, cell_name, pos, name, rot):

        self.ws = ws
        self.cv = cv
        
        self.pos = np.asarray(pos)
        if lib_name in pos_table and cell_name in pos_table[lib_name]:
            # self.pos += pos_table[lib_name][cell_name]

            self.vpos = transform(self.pos+pos_table[lib_name][cell_name])
        else:
            self.vpos = transform(self.pos)

        if rot[0] != 'M':
            self.mirrored = False
            self.rot = int(rot[1:])
        else:
            self.mirrored = rot[1]  # will be 'X' or 'Y'
            if len(rot) > 2:
                self.rot = int(rot[3:])
            else:
                self.rot = 0

        self.lib_name = lib_name
        self.cell_name = cell_name
        self.name = name

        inst_cv = ws.db.open_cell_view(lib_name, cell_name, "symbol")
        inst = ws.sch.create_inst(self.cv, inst_cv, name, list(self.vpos), rot)
        # inst = ws.sch.create_inst("analogLib", "nfet", "D0", [0., 0.], "R0")


        self.inst_cv = inst_cv
        self.inst = inst

        self.applied_params = {}
        self.params = _Params(self)
        self.pins = _Pins(self)
        # if cell_name == 'dgxnfet':
        #     self.params['s'] = 0
        #     self.params['d'] = 0

    def __setitem__(self, key, value):
        self.applied_params[key] = value
        self.params[key] = value

    def __getitem__(self, key):
        return self.params[key].value

    def __repr__(self):
        repr = ""
        repr += "Instance Name:\n\t"
        repr += self.name
        repr += "\n"
        repr += "Library Name:\n\t"
        repr += self.lib_name
        repr += "\n"
        repr += "Cell Name:\n\t"
        repr += self.cell_name
        repr += "\n"

        repr += "Pin Names: \n\t"
        for p in self.pins.names:
            repr += p
            repr += ", "

        repr += "\n"

        repr += "Parameter Names: \n\t"
        for p in self.params:
            repr += p.name
            repr += ", "
        repr += "\n"

        repr += "Applied Parameters: \n"
        for p in self.applied_params:
            repr += "\t"
            repr += p
            repr += " = "
            repr += self.applied_params[p]
            repr += "\n"
        return repr
