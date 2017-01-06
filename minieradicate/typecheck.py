from dis import Bytecode

from minieradicate.bytecode.cfg import CFG


def check(function, globals):
    bytecode = Bytecode(function.__code__)
    cfg = CFG(function.__code__).build()
    for instr in bytecode:
        print(instr)