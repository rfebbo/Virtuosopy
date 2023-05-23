import numpy as np
import regex as re
from collections.abc import Callable

snap_spacing = 0.0625

# used for recentering objects if you don't like where the center was defined
pos_table = {}

pos_table['cmos10lpe'] = {}
pos_table['cmos10lpe']['dgxnfet'] = [-0.25/snap_spacing, 0.]
pos_table['cmos10lpe']['dgxpfet'] = [-0.25/snap_spacing, 0.]
pos_table['cmos10lpe']['nfet'] = [-0.25/snap_spacing, 0.]
pos_table['cmos10lpe']['pfet'] = [-0.25/snap_spacing, 0.]

pos_table['analogLib'] = {}
pos_table['analogLib']['pmos4'] = [-0.25/snap_spacing, 0.]
pos_table['analogLib']['nmos4'] = [-0.25/snap_spacing, 0.]
pos_table['analogLib']['res'] = [0., 3.]

def print_info(instance):
    has_prop = False
    print("-----------inst dir-----------")
    for key in dir(instance.inst):
        res = getattr(instance.inst, key)
        if res != None:
            if key == "prop":
                has_prop = True
            print(f"{key} {res}")

    if has_prop:
        print("-----------props-----------")
        for prop in instance.inst.prop:
            print(f"{prop.name}")
    print("-----------inst terms-----------")
    for key in instance.inst.inst_terms:
        print(dir(key))
        print(f"-----------inst terms.{key}-----------")
        for sub_key in dir(key):
            res = getattr(key, sub_key)
            if res != None:
                print(f"{sub_key} {res}")

    print("-----------inst header-----------")
    for key in dir(instance.inst.inst_header):

        res = getattr(instance.inst.inst_header, key)
        if res != None:
            print(f"{key} {res}")

            if key == "instances":
                print(dir(instance.inst.inst_header.instances[0]))


def transform(pos):
    t_pos = []
    for n in pos:
        t_pos.append(n * snap_spacing)
    return np.asarray(t_pos)


def i_transform(pos):
    t_pos = []
    for n in pos:
        t_pos.append(n / snap_spacing)
    return np.asarray(t_pos)


# from https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
def rotate(p, origin: tuple[int,int] = (0, 0), degrees=0):
    angle = np.deg2rad(degrees)
    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    o = np.atleast_2d(origin)
    p = np.atleast_2d(p)
    return np.squeeze((R @ (p.T - o.T) + o.T).T)


def calc_center(bBox):
    w = bBox[1][0] - bBox[0][0]
    h = bBox[1][1] - bBox[0][1]

    x = bBox[0][0] + (w / 2)
    y = bBox[0][1] + (h / 2)
    return [x, y]


class internal_iter:
    def __init__(self, obj, keys):
        self._obj = obj
        self._iter = iter(keys)
        self._index = 0

    def __next__(self):
        return getattr(self._obj, next(self._iter))

def create_wave(voltages, period, rise_time = 200e-12):
    v_cycle = []
    for i, v in enumerate(voltages):
        v_cycle.append((i*period, v))

    return get_tv_pairs(v_cycle, rise_time)

# applies a list of (time, voltage) pairs to a vpwl voltage source instance
# vcycle = [(0., 3.3), (1*period, 1.5), (2*period, 3.3)]
def get_tv_pairs(v_cycle, rise_time = 200e-12):
    

    add_rt = 0
    tv_pairs = []
    for i in range(len(v_cycle)):
        t = str(v_cycle[i][0] + rise_time * add_rt)
        v = str(v_cycle[i][1])
        tv_pairs.append(t)
        tv_pairs.append(v)
        # vw[f't{i*2+1}'] = str(v_cycle[i][0] + rise_time * add_rt)
        # vw[f'v{i*2+1}'] = str(v_cycle[i][1])

        # check we arent on the last v_cycle
        if i < len(v_cycle) - 1:
            t = str(v_cycle[i+1][0])
            v = str(v_cycle[i][1])
            tv_pairs.append(t)
            tv_pairs.append(v)
            # vw[f't{i*2+2}'] = str(v_cycle[i+1][0])
            # vw[f'v{i*2+2}'] = str(v_cycle[i][1])
            add_rt = 1

    # for i, (t, v) in enumerate(tv_pairs):
    #     vw[f't{i+1}'] = t
    #     vw[f'v{i+1}'] = v
    
    return str(tv_pairs).replace('[', '').replace(']', '').replace(',', '').replace("'", '')


# convert strings like 400n to 400e-9 or 0.4u to 400e-9
def convert_str_to_num(string):
    # look for a number with or without a decimal 
    # followed by 0 or more numbers then a lower case or upper case letter
    res = re.findall('(\d+\.?\d*)([a-z]|[A-Z])', string)
    num = 0
    if len(res) > 0:
        n = float(res[0][0])
        ext = res[0][1]


        if ext == 'f':
            num = n * 1e-15
        elif ext == 'p':
            num = n * 1e-12
        elif ext == 'n':
            num = n * 1e-9
        elif ext == 'u':
            num = n * 1e-6
        elif ext == 'm':
            num = n * 1e-3
        elif ext == 'k' or ext == 'K':
            num = n * 1e3
        elif ext == 'M':
            num = n * 1e6
        elif ext == 'G':
            num = n * 1e9
        elif ext == 'T':
            num = n * 1e12
        else:
            return float(string)
    else:
        return string
        # raise(Exception(f'Could not convert {string} into a number'))
    
    return num

# ([pin of other instance, pin_name], direction)
class ConnPos:
    def __init__(self, external_pin, internal_pin, direction, offset=10, net_name=None, add_pin=False):
        self.external_pin = external_pin
        self.internal_pin = internal_pin
        self.direction = direction
        self.net_name = net_name
        self.add_pin = True

        if self.direction in ['above', 'up']:
            self.pos1 = external_pin.pos + [0., offset]
            self.label_offset = [0., offset/2]
        elif self.direction in ['below', 'down']:
            self.pos1 =  external_pin.pos - [0., offset]
            self.label_offset =  [0., offset/2]
        elif self.direction == 'left':
            self.pos1 =  external_pin.pos - [offset, 0.]
            self.label_offset =  [offset/2, 0.]
        elif self.direction == 'right':
            self.pos1 =  external_pin.pos + [offset, 0.]
            self.label_offset =  [offset/2, 0.]
        elif self.direction == 'upright':
            self.pos1 =  external_pin.pos + [offset, offset]
            self.label_offset =  [offset/2, offset/2]




def rv_condition(function_pointer : str, rv: str) -> bool:
    function_pointer = repr(function_pointer)
    rv_idx_1 = function_pointer.find('=>')
    rv_idx_2 = function_pointer[rv_idx_1:].find(r'\n') + rv_idx_1
    
    if min(rv_idx_1, rv_idx_2) != -1 and rv in function_pointer[rv_idx_1:rv_idx_2].lower():
        return True
    return False

def fn_name_condition(function_pointer : str, fn_name: str) -> bool:

    fn_name_idx = function_pointer.find('(')
    if fn_name_idx != -1 and fn_name in function_pointer[0:fn_name_idx].lower():
        
        return True
    return False

def search_sb(search_string: str, ws, path: str, condition:Callable[[str, str], bool]=fn_name_condition, max_depth: int=3):
    search_string = search_string.lower()

    for fn in dir(ws):
        # exclude primative class funcitons and recursive connections
        if '__' in fn or fn in path:
            continue

        function_pointer = getattr(ws, fn)
        # exclude non skillbridge functions
        if 'RemoteFunction' not in str(type(function_pointer)) and 'FunctionCollection' not in str(type(function_pointer)):
            continue
            

        if condition(str(function_pointer), search_string):
            print(f'found {path}.{fn}')
            print(str(function_pointer))
        

        p = path + f'.{fn}'
        if p.count('.') < max_depth:
            search_sb(search_string, function_pointer, p, condition=condition, max_depth=max_depth)
