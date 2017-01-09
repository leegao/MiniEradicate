from dis import Instruction, stack_effect
from functools import reduce
from typing import Dict, Tuple

from minieradicate.analysis.domain import PythonEnvironment, LocalsDomain, Tagged, StackDomain, GlobalsDomain, D
from minieradicate.bytecode.cfg import CFG


class State(object):
    def __init__(
            self,
            before: Dict[Instruction, PythonEnvironment] = None,
            after: Dict[Instruction, PythonEnvironment] = None,
            edges: Dict[Tuple[int, int], PythonEnvironment] = None):
        self.before = before if before else {}
        self.after = after if after else {}
        self.edges = edges if edges else {}

    @classmethod
    def make(cls, cfg: CFG, init: Dict[Instruction, PythonEnvironment] = None):
        after = {}
        before = {}
        edges = {}
        if not init: init = {}
        for block in cfg.blocks:
            for instr in block:
                after[instr] = None
                if instr in init:
                    before[instr] = init[instr]
                else:
                    before[instr] = None
        for i, js in cfg.edges.items():
            for j in js:
                edges[i, j] = None
        return State(before, after, edges)


class Dataflow(object):
    def __init__(self, function, external):
        self.function = function
        self.annotations = function.__annotations__
        self.varnames = function.__code__.co_varnames
        self.external = external
        self.cfg = CFG(function.__code__).build()

    def domain(self, *args) -> D:
        raise NotImplementedError()

    def from_type(self, type) -> D:
        raise NotImplementedError()

    def transfer_cfg(self, state: State) -> (State, bool):
        old_state = state
        state = State(dict(state.before), dict(state.after), dict(state.edges))
        changed = False
        # just go through the cfg
        for i, block in enumerate(self.cfg.blocks):
            if i in self.cfg.dead_nodes: continue
            # compute the before state
            if i in self.cfg.reverse_edges:
                join = reduce(
                    lambda a, b: a | b,
                    (state.edges[j, i] for j in self.cfg.reverse_edges[i] if state.edges[j, i]))
            else:
                join = state.before[block[0]] or PythonEnvironment()
            if not old_state.before[block[0]] or old_state.before[block[0]] != join:
                changed = True
                state.before[block[0]] = join
            # propagate this through the block
            env = join
            for instr in block:
                state.before[instr] = env
                state.after[instr] = self.transfer(instr, env)
                if state.after[instr] != old_state.after[instr]:
                    changed = True
                env = state.after[instr]
            # at the end, propagate env to the edges
            # assume for now that the propagation is flow insensitive
            if i in self.cfg.edges:
                for j in self.cfg.edges[i]:
                    assert (i, j) in state.edges
                    state.edges[i, j] = env
        return state, changed

    def load_const(self, instr: Instruction, _: PythonEnvironment):
        return [self.domain(instr.argval)]

    def store_fast(self, instr: Instruction, env: PythonEnvironment):
        env.locals[instr.arg] = env.stack.pop(-1)
        return []

    def load_fast(self, instr: Instruction, env: PythonEnvironment):
        return [env.locals[instr.arg] if instr.arg in env.locals else self.domain(None)]

    def transfer(self, instr: Instruction, env: PythonEnvironment) -> (PythonEnvironment, bool):
        env = PythonEnvironment(
            StackDomain(env.stack),
            LocalsDomain(env.locals),
            GlobalsDomain(env.globals),
            list(env.shape))

        effect = stack_effect(instr.opcode, instr.arg)
        if instr.opname == 'POP_BLOCK':
            effect = -env.shape.pop(-1)
        else:
            env.shape[-1] += effect
        if instr.opname == 'SETUP_LOOP': env.shape.append(0)
        if hasattr(self, instr.opname.lower()):
            oldStackSize = len(env.stack)
            for domain in getattr(self, instr.opname.lower())(instr, env):
                env.stack.append(Tagged({instr}, domain))
            effect = stack_effect(instr.opcode, instr.arg)
            assert len(env.stack) - oldStackSize == effect
        else:
            if effect < 0:
                # pop effect off of stack
                for domain in range(-effect): env.stack.pop(-1)
            elif effect > 0:
                # push NonNulls on
                for domain in range(effect): env.stack.append(Tagged({instr}, self.domain()))
        return env

    def solve(self):
        # Make initials
        init = {
            self.cfg.blocks[0][0]: PythonEnvironment(
                None,
                LocalsDomain(
                    {self.varnames.index(key): Tagged(set(), self.from_type(self.annotations[key]))
                     for key in self.annotations if key != 'return'}))
        }
        state, changed = self.transfer_cfg(State.make(self.cfg, init))
        while changed:
            state, changed = self.transfer_cfg(state)

        output = reduce(lambda x, y: x | y, (state.before[ret].stack[-1] for ret in self.cfg.returns))
        return state, output
