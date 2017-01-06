from typing import List, TypeVar, Dict, overload, Tuple

from minieradicate.bytecode.cfg import CFG
from dis import Instruction

class Domain(object):
    def __le__(self, other : 'D'): ...

    def __or__(self, other : 'D'): ...

    def __and__(self, other : 'D'): ...

D = TypeVar('D', bound = Domain)
class StackDomain(List[D], Domain):
    def __le__(self, other):
        assert len(self) == len(other)
        list = []
        for i, left in enumerate(self):
            list.append(left.__le__(other[i]))
        return all(list)

    def __or__(self, other):
        assert len(self) == len(other)
        list = []
        for i, left in enumerate(self):
            list.append(left.__or__(other[i]))
        return StackDomain(list)

    def __and__(self, other):
        assert len(self) == len(other)
        list = []
        for i, left in enumerate(self):
            list.append(left.__and__(other[i]))
        return StackDomain(list)

class LocalsDomain(Dict[int, D], Domain):
    def __le__(self, other : 'LocalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__le__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return all(map.values())

    def __or__(self, other : 'LocalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__or__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return LocalsDomain(map)

    def __and__(self, other : 'LocalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__and__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return LocalsDomain(map)

class GlobalsDomain(Dict[str, D], Domain):
    def __le__(self, other: 'GlobalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__le__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return all(map.values())

    def __or__(self, other: 'GlobalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__or__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return GlobalsDomain(map)

    def __and__(self, other: 'GlobalsDomain'):
        map = {}
        for k, v in self.items():
            if k in other:
                map[k] = v.__and__(other[k])
            else:
                map[k] = v
        for k, v in other.items():
            if k not in self:
                map[k] = v
        return GlobalsDomain(map)

class NullabilityDomain(Domain):
    def __init__(self, n : int):
        self.n = n

    def __le__(self, other : 'NullabilityDomain'):
        return self.n < other.n

    def __or__(self, other : 'NullabilityDomain'):
        return NullabilityDomain(self.n | other.n)

    def __and__(self, other : 'NullabilityDomain'):
        return NullabilityDomain(self.n & other.n)

    def __eq__(self, other : 'NullabilityDomain'):
        return self.n == other.n

    def __repr__(self):
        return str(bool(self.n))

class PythonEnvironment(Domain):
    def __init__(self, stack : StackDomain = None, locals : LocalsDomain = None, globals : GlobalsDomain = None):
        self.stack = stack or StackDomain()
        self.locals = locals or LocalsDomain()
        self.globals = globals or GlobalsDomain()

    def __le__(self, other : 'PythonEnvironment'):
        stack = self.stack.__le__(other.stack)
        locals = self.locals.__le__(other.locals)
        globals = self.globals.__le__(other.globals)
        return stack and locals and globals

    def __or__(self, other : 'PythonEnvironment'):
        stack = self.stack.__or__(other.stack)
        locals = self.locals.__or__(other.locals)
        globals = self.globals.__or__(other.globals)
        return PythonEnvironment(stack, locals, globals)

    def __and__(self, other : 'PythonEnvironment'):
        stack = self.stack.__and__(other.stack)
        locals = self.locals.__and__(other.locals)
        globals = self.globals.__and__(other.globals)
        return PythonEnvironment(stack, locals, globals)

    def __eq__(self, other : 'PythonEnvironment'):
        stack = self.stack.__eq__(other.stack)
        locals = self.locals.__eq__(other.locals)
        globals = self.globals.__eq__(other.globals)
        return stack and locals and globals

    def __str__(self):
        return '<%s; %s; %s>' % (self.stack, self.locals, self.globals)


def transfer(instr : Instruction, env : PythonEnvironment) -> (PythonEnvironment, bool):
    return env, False


def transfer_cfg(cfg : CFG, env : PythonEnvironment) -> (PythonEnvironment, bool):
    return enumerate, False

def check(function, globals):
    cfg = CFG(function.__code__).build()
    # print(cfg.dot())
    env, changed = transfer_cfg(cfg, PythonEnvironment())
    while changed:
        env, changed = transfer_cfg(cfg, env)