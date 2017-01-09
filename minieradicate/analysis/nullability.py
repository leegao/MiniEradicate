from dis import Instruction

from minieradicate.analysis.dataflow import Dataflow
from minieradicate.analysis.domain import Domain, PythonEnvironment


class NullabilityDomain(Domain):
    def __init__(self, n : bool):
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
        return 'Optional' if self.n else 'NotNull'

    @classmethod
    def abstract(cls, object):
        return NullabilityDomain(object == None)


def is_nullable(object):
    return object == None or \
           object == type(None) or \
           (hasattr(object, '__union_set_params__') and type(None) in object.__union_set_params__)


class NullabilityAnalysis(Dataflow):
    def from_type(self, type):
        return NullabilityDomain(is_nullable(type))

    def domain(self, *args):
        if args:
            return NullabilityDomain.abstract(*args)
        else:
            return NullabilityDomain(False)

    def call_function(self, instr: Instruction, env: PythonEnvironment):
        args = []
        for i in range(instr.arg): args.insert(0, env.stack.pop())
        method = env.stack.pop()
        out = NullabilityDomain(False)
        for tag in method.tags:
            if tag.opname == 'LOAD_GLOBAL' and tag.argval in self.external:
                var = self.external[tag.argval]
                if hasattr(var, '__annotations__') and 'return' in var.__annotations__:
                    out |= NullabilityDomain(is_nullable(var.__annotations__['return']))
        return [out]