import copy
import random

from attribute import IntegerAttribute
from attribute import RealAttribute
from attribute import NominalAttribute
from attribute import OrdinalAttribute
from attribute import BinaryAttribute
from Cython.Compiler.Naming import self_cname
from input import Input

__author__="Marcos Gabarda"
__date__ ="$06-dic-2010 16:28:24$"

class InputSet:
    """

    Class to enclose a data set.

    @type __data: list(Input)
    @type __missing: float
    """
    __data = []
    __missing = None
    sup = None
    outputs = None
    mode = "cls"
        
    def load(self, file):
        # @type file: str
        f = open (file, 'r')
        if not f:
            print "Fichero " + f + " no enconctrado.\n"
            exit(-1)
        lines = f.readlines()
        f.close()

        self.__missing = 0.0

        # Read header from file
        self.mode = lines[0].split()[0]
        n_attrs = int(lines[1])
        missing_code = lines[2].split()[0]
        self.outputs = 0
        header = []
        header_extra = []
        for i in range(3, n_attrs + 3):
            line = lines[i]
            line_list = line.split()
            header.append(line_list[0])
            if line_list[0] == "set" or line_list[0] == "ord":
                header_extra.append(line_list[1:])
            else:
                header_extra.append([])
            if line_list[0] == "class":
                self.outputs += 1

        # Read data from file
        for i in range(n_attrs + 3, len(lines)):
            raw_attributes = lines[i].split(',')
            target = []
            attributes = []
            fix_class_index = 0
            for i, v in enumerate(raw_attributes):
                if header[i] == "class":
                    """
                    Class attribute.
                    """
                    fix_class_index += 1
                    target.append(v.strip())
                elif header[i] == "int":
                    """
                    Integer attribute creation.
                    """
                    attr = IntegerAttribute()
                    attr.index = i-fix_class_index
                    if str(v) == str(missing_code):
                        self.__missing += 1
                        attr.missing = True
                    else:
                        attr.value = int(v.strip().split(".")[0])
                    attr.data_set = self
                    attributes.append(attr)
                elif header[i] == "real":
                    """
                    Real attribute creation.
                    """
                    attr = RealAttribute()
                    attr.index = i-fix_class_index
                    if v == missing_code:
                        self.__missing += 1
                        attr.missing = True
                    else:
                        v_final = float(v.strip())
                        attr.value = v_final
                        if not self.sup or self.sup < v_final:
                            self.sup = v_final
                    attr.data_set = self
                    attributes.append(attr)
                elif header[i] == "set":
                    """
                    Nominal attribute creation.
                    """
                    attr = NominalAttribute()
                    attr.index = i-fix_class_index
                    attr.headers = header_extra[i]
                    if v == missing_code:
                        self.__missing += 1
                        attr.missing = True
                    else:
                        attr.value = v.strip().split(".")[0]
                    attr.data_set = self
                    attributes.append(attr)
                elif header[i] == "ord":
                    """
                    Ordinal attribute creation.
                    """
                    attr = OrdinalAttribute()
                    attr.index = i-fix_class_index
                    attr.headers = header_extra[i]
                    if v == missing_code:
                        self.__missing += 1
                        attr.missing = True
                    else:
                        attr.value = v.strip().split(".")[0]
                    attr.data_set = self
                    attributes.append(attr)
                elif header[i] == "bin":
                    """
                    Binary attribute creation.
                    """
                    attr = BinaryAttribute()
                    attr.index = i-fix_class_index
                    if v == missing_code:
                        self.__missing += 1
                        attr.missing = True
                    else:
                        attr.value = int(v.strip().split(".")[0])
                    attr.data_set = self
                    attributes.append(attr)
                elif header[i] == "fuzzy":
                    # TODO Implement
                    pass
                else:
                    # TODO Handle error
                    pass
            input = Input(attributes)
            input.target = target
            self.__data.append(input)

    def size(self):
        return len(self.__data)
    
    def missing(self):
        return (self.__missing / (float(self.size())*len(self.__data[0].attributes))) * 100

    def get_attribute_probability(self, index, value):
        # Get probability
        attr_list = []
        attr_count = 0.0
        for i,v in enumerate(self.__data):
            attr_list.append(v.attributes[index])
            if v.attributes[index].value == value:
                attr_count += 1.0
        return float(attr_count/float(len(attr_list)))


    def get(self, index):
        if index < 0 or index >= self.size():
            return None
        return self.__data[index]

    def get_nearest(self, index, q, exclusion=[]):
        objective = self.get(index)
        if not objective:
            return None
        similarities = []
        exclusion_list = copy.deepcopy(exclusion)
        exclusion_list.append(index)
        for i in range(self.size()):
            if i not in exclusion_list:
                t = (i, objective.similarity(self.__data[i], q))
                similarities.append(t)
        sorted_similarities = \
            sorted(similarities, key=lambda similarities: similarities[1])
        return sorted_similarities[len(sorted_similarities) - 1][0]

    def split(self, size):
        size_part = size
        if size <= 0 or size > self.size():
            size_part = self.size()
        indexes = range(self.size())
        random.shuffle(indexes)
        sub_sets = []
        sub_sets.append(InputSubSet(indexes[:size_part], self))
        sub_sets.append(InputSubSet(indexes[size_part:], self))
        return sub_sets
    
    def split_folds(self, folds):
        size_part = self.size() / folds
        extra = self.size() % folds
        indexes = range(self.size())
        random.shuffle(indexes)
        sub_sets = []
        for i in range(folds):
            sub_sets.append(InputSubSet(indexes[i*size_part:i*size_part+size_part], self))
        for i in range(extra):
            sub_sets[i].add(indexes[len(indexes) - (i + 1)])
        return sub_sets

class InputSubSet:
    __indexes = []
    __data_set = None
    def __init__(self, indexes, data_set):
        self.__indexes = indexes
        self.__data_set = data_set
    def get_data(self):
        return self.__indexes
    def size(self):
        return len(self.__indexes)
    def get(self, index):
        if index < 0 or index >= self.size():
            return None        
        return self.__data_set.get(self.__indexes[index])
    def add(self, index):
        # @type index: int
        if index in self.__indexes:
            return False
        self.__indexes.append(index)
        return True
    def targets(self, index):
        t = []
        for i in range(len(self.__indexes)):
            inp = self.get(i)
            t_comp = float(inp.target[index])
            if self.__data_set.mode == "cls":
                if t_comp == 1.0:
                    t_comp = 0.9
                elif t_comp == 0.0:
                    t_comp = 0.1
            t.append(t_comp)
        return t
    def __str__(self):
        return str(self.__indexes)


if __name__ == "__main__":
    data_set = InputSet()
    data_set.load("../data/splice.data")
    print data_set.missing()
