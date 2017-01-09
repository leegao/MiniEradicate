from typing import Optional, T

from minieradicate.typecheck import check

def bar(x : T) -> Optional[T]:
    return 1 if x.foo() else None

def foo(z : Optional[T]) -> None:
    return bar(z)

check(foo, locals())
check(bar, locals())