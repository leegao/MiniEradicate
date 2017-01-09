from typing import Optional, T

from minieradicate.typecheck import check

def bar(x : T) -> Optional[T]:
    return 1 if x.foo() else None

def foo(z : Optional[T]) -> None:
    return bar(z)

items = locals().items()
for k,v in list(items):
    if hasattr(v, '__annotations__'):
        print(k, check(v, locals()))