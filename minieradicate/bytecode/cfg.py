from collections import defaultdict
from dis import Bytecode
from opcode import hasjrel, hasjabs, opmap, opname

ABS = set(hasjabs)
REL = set(hasjrel)

GOTOS = {opmap['CONTINUE_LOOP'], opmap['JUMP_FORWARD']}

class CFG(object):
    def __init__(self, code):
        self.code = code # type: code
        self.bytecode = Bytecode(code)

    def build(self):
        # find basic blocks, which is headed by the first instruction or jump target
        blocks = [[]]
        targets = {}
        for instr in self.bytecode:
            if blocks[-1] and instr.is_jump_target:
                blocks.append([instr])
                continue
            blocks[-1].append(instr)
            if instr.opcode in ABS or instr.opcode in REL or instr.opcode == 83:
                blocks.append([])
        if not blocks[-1]:
            blocks.pop(-1)

        for i, block in enumerate(blocks):
            targets[block[0].offset] = i

        edges = defaultdict(set) # from -> to

        for i, block in enumerate(blocks):
            if block[-1].opcode == opmap['RETURN_VALUE']:
                continue
            if block[-1].opcode not in GOTOS:
                if i + 1 < len(blocks):
                    edges[i].add(i + 1)
            target = block[-1].argval
            if target:
                if target in REL: target += i
                edges[i].add(targets[target])

        # for i, block in enumerate(blocks):
        #     print(i, block)
        #     print(edges[i])

        self.blocks = blocks
        self.edges = dict(edges)
        return self

    def dot(self):
        output = ''
        for i, block in enumerate(self.blocks):
            output += '  %s [label="%s"];\n' % (
                i,
                '\n'.join(str(instr.offset) + '  ' + instr.opname + ('(%s)' % instr.argval if instr.arg is not None else '') for instr in block))
        for i in self.edges:
            for j in self.edges[i]:
                output += '  %s -> %s;\n' % (i, j)

        return 'digraph cfg {\n%s}' % output