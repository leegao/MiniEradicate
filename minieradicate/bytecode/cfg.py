from dis import Bytecode


class CFG(object):
    def __init__(self, code):
        self.code = code
        self.bytecode = Bytecode(code)

    def build(self):
        # find basic blocks, which is headed by the first instruction or jump target
        blocks = [[]]
        for instr in self.bytecode:
            if blocks[-1] and instr.is_jump_target:
                blocks.append([instr])
                continue
            blocks[-1].append(instr)
        print(blocks)
        return self