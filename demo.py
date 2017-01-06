from typing import no_type_check

from minieradicate.annotations import Nullable
from minieradicate.typecheck import check

@no_type_check
def bar(x : Nullable) -> Nullable:
    return x

@no_type_check
def foo(z : ...) -> ...:
    for y in z:
        bar(z, y), 3

check(foo, locals())