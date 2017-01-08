from typing import no_type_check, Optional, T

from minieradicate.typecheck import check

@no_type_check
def bar(x : T) -> Optional[T]:
    return 1 if x.foo() else None

@no_type_check
def foo(z : Optional[T]) -> None:
    return bar(z)

check(foo, locals())
check(bar, locals())