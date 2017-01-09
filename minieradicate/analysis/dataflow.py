from dis import Instruction
from functools import reduce
from typing import Dict, Tuple

from minieradicate.analysis.domain import PythonEnvironment, LocalsDomain, Tagged
from minieradicate.bytecode.cfg import CFG


class State(object):
    def __init__(
            self,
            before : Dict[Instruction, PythonEnvironment] = None,
            after : Dict[Instruction, PythonEnvironment] = None,
            edges : Dict[Tuple[int, int], PythonEnvironment] = None):
        self.before = before if before else {}
        self.after = after if after else {}
        self.edges = edges if edges else {}

    @classmethod
    def make(cls, cfg : CFG, init : Dict[Instruction, PythonEnvironment] = None):
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


class Dataflow():
    def __init__(self, function, external):
        self.function = function
        self.annotations = function.__annotations__
        self.varnames = function.__code__.co_varnames
        self.external = external
        self.cfg = CFG(function.__code__).build()

    def domain(self, *args):
        raise NotImplementedError()

    def transfer(self, instr : Instruction, env : PythonEnvironment):
        raise NotImplementedError()

    def transfer_cfg(self, state: State) -> (State, bool):
        oldState = state
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
            if not oldState.before[block[0]] or oldState.before[block[0]] != join:
                changed = True
                state.before[block[0]] = join
            # propagate this through the block
            env = join
            for instr in block:
                state.before[instr] = env
                state.after[instr] = self.transfer(instr, env)
                if state.after[instr] != oldState.after[instr]:
                    changed = True
                env = state.after[instr]
            # at the end, propagate env to the edges
            # assume for now that the propagation is flow insensitive
            if i in self.cfg.edges:
                for j in self.cfg.edges[i]:
                    assert (i, j) in state.edges
                    state.edges[i, j] = env
        return state, changed

    def solve(self):
        # Make initials
        init = {
            self.cfg.blocks[0][0]: PythonEnvironment(
                None,
                LocalsDomain(
                    {self.varnames.index(key) : Tagged(set(), self.domain(self.annotations[key]))
                    for key in self.annotations if key != 'return'}))
        }
        state, changed = self.transfer_cfg(State.make(self.cfg, init))
        while changed:
            state, changed = self.transfer_cfg(state)

        output = reduce(lambda x, y: x | y, (state.before[ret].stack[-1] for ret in self.cfg.returns))
        return state, output