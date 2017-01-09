from typing import List, TypeVar, Dict, Tuple, Any, Set
from dis import Instruction

class Domain(object):
    def __le__(self, other : 'D'): ...

    def __or__(self, other : 'D'): ...

    def __and__(self, other : 'D'): ...

    @classmethod
    def abstract(cls, object):
        raise NotImplementedError()

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

class Tagged(Domain):
    def __init__(self, tags : Set[Instruction], d : Domain):
        self.tags = tags
        self.d = d

    def __and__(self, other : 'Tagged'):
        tags = self.tags | other.tags
        return Tagged(tags, self.d & other.d)

    def __eq__(self, other : 'Tagged'):
        return self.tags == other.tags and self.d == other.d

    def __repr__(self):
        return '%s (from %s)' % (self.d, {tag.offset for tag in self.tags})

    def __le__(self, other: 'Tagged'):
        return self.d <= other.d

    def __or__(self, other: 'Tagged'):
        tags = self.tags | other.tags
        return Tagged(tags, self.d | other.d)