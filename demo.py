from minieradicate.annotations import Nullable
from minieradicate.typecheck import check

def bar(x : Nullable) -> Nullable:
    return x


def foo(z : ...) -> ...:
    return bar(z, y), 3

check(foo, locals())