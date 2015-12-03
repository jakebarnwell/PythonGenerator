import itertools
import pygame
import time
import pickle
import os

#from .
import nsgaii
import field

"""
Each cell has three states - dead, alive and old
(old cells are alive but cannot reproduce).

For each "alive" cell, the act of reproduction is called --
replacing cell and its  neighborhood (3x3 square) with a new neighborhood
from gene.

The process of growth always starts with one alive cell in the center of fields
and continues for given amount of iterations.

"""

STATE_COLORS = {
    0: (0, 0, 0), # dead: black
    1: (255, 0, 0), # alive: red
    2: (255, 255, 255), # old: white
}

class Evolver(nsgaii.Problem):

    N = 100 # population size
    n = 5*5 * (3 * 3) # for each of the 4 * 4 states, next state with dimensions 3*3
    var_bounds = [0.0, 1.0]
    G = 20000

    def __init__(self, field, growthIterations):
        self.fieldW = field[0]
        self.fieldH = field[1]
        self.growIter = growthIterations

        pygame.init()
        self.screen = pygame.display.set_mode((self.fieldW, self.fieldH))
        super(Evolver, self).__init__()

    def saveField(self, field, name):
        for _y in xrange(self.fieldH):
            for _x in xrange(self.fieldW):
                _pos = _y * self.fieldH + _x
                _cell = field.field[_pos]
                _color = STATE_COLORS[_cell]
                self.screen.set_at((_x, _y), _color)
        pygame.display.flip()
        pygame.image.save(self.screen, name)

    def processNonDominatedFront(self, gen, front):
        for (_id, _el) in enumerate(front):
            self.saveField(
                _el.field,
                os.path.join(
                    "saves",
                    "gen_%s_pareto_%i.png" % (gen, _id)
            ))
        pickle.dump([_el.genes for _el in front],
            open(
                os.path.join("saves", "last_front.pckl"),
                "wb"
        ))

    def getSolutionResultField(self, solution):
        # get result solution field
        if not hasattr(solution, "field"):
            _stateIter = (
                int(round(_num * (field.NUM_STATES - 1)))
                for _num in solution.genes)
            _translationTable = []
            for (_stateId, _group) in itertools.groupby(
                enumerate(_stateIter), lambda el: el[0] / (3*3)):
                _translationTable.append(tuple(
                    _el[1] for _el in _group))
            _resultField = field.Field(
                self.fieldW,
                self.fieldH,
                _translationTable,
            )
            _resultField.grow(self.growIter)
            solution.field = _resultField
        return solution.field

    def alive_ratio_obj(self, solution):
        # objective for the grown tree to have
        # equal amount of alive + old cells and dead
        _dead = _alive = 0
        for _cell in self.getSolutionResultField(solution).field:
            if _cell > 0:
                _alive += 1
            else:
                _dead += 1
        return abs(_alive - _dead)

    def interconnected_obj(self, solution):
        # make 'dead' pixels to be as interconnected as possible
        _field = self.getSolutionResultField(solution)
        _sum = 0
        for _pos in xrange(len(_field.field)):
            _square = _field.getSquare(_pos)
            _myState = _square[4]
            _diag = _field.getSquareDiag(_square)
            _straight = _field.getSquareStraight(_square)
            _deadScore = 0.5 * len([_el for _el in _diag if _el == _myState]) + 1.0 * len([_el for _el in _straight if _el == _myState])
            _sum += 10.0 / (_deadScore + 1)
        return _sum

    def min_alive_obj(self, solution):
        return len([_el
            for _el in self.getSolutionResultField(solution).field
            if _el == field.STATES["ALIVE"]
        ])

    obj_funcs = [
        alive_ratio_obj,
        interconnected_obj,
        min_alive_obj,
    ] # objective functions


if __name__ == "__main__":
    _evolver = Evolver(field=(50, 50),
        growthIterations=50)
    # with field 400x400 and start on the center, the
    # minimum time it takes to fill all area is 200
    # iterations. Using double of that to get more or less
    # "mature" field
    _evolver.experiment()
    print "done."

# vim: set sts=4 sw=4 et :
