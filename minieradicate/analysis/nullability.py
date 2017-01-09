from dis import Instruction, stack_effect
from typing import Dict, Any

from minieradicate.analysis.dataflow import Dataflow
from minieradicate.analysis.domain import Domain, StackDomain, LocalsDomain, GlobalsDomain, Tagged, PythonEnvironment


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


def call_function(instr : Instruction, env : PythonEnvironment, globals : Dict[str, Any]):
    args = []
    for i in range(instr.arg): args.insert(0, env.stack.pop())
    method = env.stack.pop()
    out = NullabilityDomain(0)
    for tag in method.tags:
        if tag.opname == 'LOAD_GLOBAL' and tag.argval in globals:
            var = globals[tag.argval]
            if hasattr(var, '__annotations__') and 'return' in var.__annotations__:
                out |= NullabilityDomain(is_nullable(var.__annotations__['return']))
    return (Tagged({instr}, out),)


def is_nullable(object):
    return object == None or \
           object == type(None) or \
           (hasattr(object, '__union_set_params__') and type(None) in object.__union_set_params__)


class NullabilityAnalysis(Dataflow):
    def domain(self, object):
        NullabilityDomain(is_nullable(object))

    def transfer(self, instr: Instruction, env: PythonEnvironment) -> (PythonEnvironment, bool):
        env = PythonEnvironment(
            StackDomain(env.stack),
            LocalsDomain(env.locals),
            GlobalsDomain(env.globals),
            list(env.shape))
        switch = {
            'LOAD_CONST': lambda: (Tagged({instr}, NullabilityDomain(1 if instr.argrepr == 'None' else 0)),),
            'STORE_FAST': lambda: env.locals.__setitem__(instr.arg, env.stack.pop(-1)) or (),
            'LOAD_FAST': lambda: (
            env.locals[instr.arg] if instr.arg in env.locals else Tagged({instr}, NullabilityDomain(0)),),
            'CALL_FUNCTION': lambda: call_function(instr, env, self.external),
        }

        effect = stack_effect(instr.opcode, instr.arg)
        if instr.opname == 'POP_BLOCK':
            effect = -env.shape.pop(-1)
        else:
            env.shape[-1] += effect
        if instr.opname == 'SETUP_LOOP': env.shape.append(0)
        if instr.opname in switch:
            oldStackSize = len(env.stack)
            for tag in switch[instr.opname](): env.stack.append(tag)
            effect = stack_effect(instr.opcode, instr.arg)
            assert len(env.stack) - oldStackSize == effect
        else:
            if effect < 0:
                # pop effect off of stack
                for tag in range(-effect): env.stack.pop(-1)
            elif effect > 0:
                # push NonNulls on
                for tag in range(effect): env.stack.append(Tagged({instr}, NullabilityDomain(0)))
        return env

