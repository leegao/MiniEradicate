from functools import reduce
from pprint import pprint
from typing import List, TypeVar, Dict, overload, Tuple

from minieradicate.bytecode.cfg import CFG
from dis import Instruction, stack_effect

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
        self.n = 1 if n else 0

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
    def __init__(
            self,
            stack : StackDomain = None,
            locals : LocalsDomain = None,
            globals : GlobalsDomain = None,
            shape : List[int] = None,):
        self.stack = stack or StackDomain()
        self.locals = locals or LocalsDomain()
        self.globals = globals or GlobalsDomain()
        self.shape = shape or [0]

    def __le__(self, other : 'PythonEnvironment'):
        stack = self.stack.__le__(other.stack)
        locals = self.locals.__le__(other.locals)
        globals = self.globals.__le__(other.globals)
        return stack and locals and globals

    def merge_shape(self, other : 'PythonEnvironment'):
        m = min(len(self.shape), len(other.shape))
        left = self.shape[:m]
        right = other.shape[:m]
        assert left == right, '%s, %s' % (left, right)
        return left

    def __or__(self, other : 'PythonEnvironment'):
        stack = self.stack.__or__(other.stack)
        locals = self.locals.__or__(other.locals)
        globals = self.globals.__or__(other.globals)
        return PythonEnvironment(stack, locals, globals, self.merge_shape(other))

    def __and__(self, other : 'PythonEnvironment'):
        stack = self.stack.__and__(other.stack)
        locals = self.locals.__and__(other.locals)
        globals = self.globals.__and__(other.globals)
        return PythonEnvironment(stack, locals, globals, self.merge_shape(other))

    def __eq__(self, other : 'PythonEnvironment'):
        if not other:
            return False
        stack = self.stack.__eq__(other.stack)
        locals = self.locals.__eq__(other.locals)
        globals = self.globals.__eq__(other.globals)and self.shape == other.shape
        return stack and locals and globals

    def __repr__(self):
        return '<%s; %s; %s>' % (self.stack, self.locals, self.globals)


class State(object):
    def __init__(
            self,
            before : Dict[Instruction, PythonEnvironment] = None,
            after : Dict[Instruction, PythonEnvironment] = None,
            edges : Dict[Tuple[int, int], PythonEnvironment] = None):
        self.before = before if before else {}
        self.after = after if after else {}
        self.edges = edges if edges else {}

    @classmethod
    def make(cls, cfg : CFG, init : Dict[Instruction, PythonEnvironment] = None):
        after = {}
        before = {}
        edges = {}
        if not init: init = {}
        for block in cfg.blocks:
            for instr in block:
                after[instr] = None
                if instr in init:
                    before[instr] = init[instr]
                else:
                    before[instr] = None
        for i, js in cfg.edges.items():
            for j in js:
                edges[i, j] = None
        return State(before, after, edges)

def transfer(instr : Instruction, env : PythonEnvironment) -> (PythonEnvironment, bool):
    env = PythonEnvironment(
        StackDomain(env.stack),
        LocalsDomain(env.locals),
        GlobalsDomain(env.globals),
        list(env.shape))

    switch = {
        'LOAD_CONST' : lambda: (1 if instr.argrepr == 'None' else 0,),
        'STORE_FAST' : lambda: env.locals.__setitem__(instr.arg, env.stack.pop(-1)) or (),
        'LOAD_FAST'  : lambda: (env.locals[instr.arg] if instr.arg in env.locals else NullabilityDomain(0),)
    }

    effect = stack_effect(instr.opcode, instr.arg)
    if instr.opname == 'POP_BLOCK': effect = -env.shape.pop(-1)
    else: env.shape[-1] += effect
    if instr.opname == 'SETUP_LOOP': env.shape.append(0)
    if instr.opname in switch:
        oldStackSize = len(env.stack)
        for i in switch[instr.opname](): env.stack.append(NullabilityDomain(i))
        effect = stack_effect(instr.opcode, instr.arg)
        assert len(env.stack) - oldStackSize == effect
    else:
        if effect < 0:
            # pop effect off of stack
            for i in range(-effect): env.stack.pop(-1)
        elif effect > 0:
            # push NonNulls on
            for i in range(effect): env.stack.append(NullabilityDomain(0))
    return env


def transfer_cfg(cfg : CFG, state : State) -> (State, bool):
    oldState = state
    state = State(dict(state.before), dict(state.after), dict(state.edges))
    changed = False
    # just go through the cfg
    for i, block in enumerate(cfg.blocks):
        # compute the before state
        if i in cfg.reverse_edges:
            # print(cfg.reverse_edges[i], i, state.edges)
            preds = [state.edges[j, i] for j in cfg.reverse_edges[i] if state.edges[j, i]]
            join = reduce(lambda a, b: a | b, preds)
        else:
            join = state.before[block[0]] or PythonEnvironment()
        if not oldState.before[block[0]] or oldState.before[block[0]] != join:
            changed = True
            state.before[block[0]] = join
        # propagate this through the block
        env = join
        for instr in block:
            state.before[instr] = env
            newEnv = transfer(instr, env)
            state.after[instr] = newEnv
            if newEnv != oldState.after[instr]:
                changed = True
            env = newEnv
        # at the end, propagate env to the edges
        # assume for now that the propagation is flow insensitive
        if i in cfg.edges:
            for j in cfg.edges[i]:
                assert (i, j) in state.edges
                state.edges[i, j] = env
    return state, changed

def check(function, globals):
    cfg = CFG(function.__code__).build()
    # print(cfg.dot())

    state = State.make(cfg)
    state, changed = transfer_cfg(cfg, state)
    while changed:
        state, changed = transfer_cfg(cfg, state)

    pprint(state.before)