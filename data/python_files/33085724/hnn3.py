import math
import numpy
import sys
import random

from hiddenneuron import HiddenNeuron
from inputset import InputSet
from inputset import InputSubSet
from outputneuron import OutputNeuron

__author__="Marcos Gabarda"
__date__ ="$04-dic-2010 18:59:24$"

class HNN3:
    """
    Heterogeneous Neuronal Network 3
    @type __data_set: InputSet
    @type __hn: list(HiddenNeuron)
    @type __on: list(OutputNeuron)
    """
    __data_set = None
    __lambda = None
    __hn = None
    __on = None
    def __init__(self, data_set, centers, gammas, q, l):
        """
        @type data_set: InputSet
        @type centers: list
        @type gammas: list
        @type q: float
        @type l: float
        """
        # TODO Check len(centers) == len(gammas)

        self.__data_set = data_set
        self.__lambda = l
        self.__hn = []
        self.__on = []

        for i,v in enumerate(centers):
            center = data_set.get(v)
            self.__hn.append(HiddenNeuron(center, gammas[i], q))
        for i in range(data_set.outputs):
            self.__on.append(OutputNeuron(data_set.mode))

    def __train_weights(self, training_data):
        # @type training_data: InputSubSet
        X = []
        for i in range(training_data.size()):
            row = []
            input = training_data.get(i)
            for j in range(len(self.__hn)):
                row.append(self.__hn[j].get_output(input))
            row.append(1.0)
            X.append(row)
        for i in range(len(self.__on)):
            self.__on[i].train(X, training_data.targets(i), self.__lambda)
    
    def set_weights(self, weights):
        if len(weights) != len(self.__on):
            sys.stderr.write('Error - Weights lenght incorrect.\n')
        for i in range(len(self.__on)):
            self.__on[i].set_weights(weights[i])

    def get_output(self, input):
        # @typo input: Input
        hidden_outputs = []
        for i in range(len(self.__hn)):
            hidden_outputs.append(self.__hn[i].get_output(input))
        outputs = []
        for i in range(len(self.__on)):
            outputs.append(self.__on[i].get_output(hidden_outputs))
        return outputs

    def get_training_accuracy(self, margin=0.5):
        """
        TODO Rename to get_test_accuracy
        """
        subsets = self.__data_set.split(int(self.__data_set.size()*0.75))
        training = subsets[0]
        test = subsets[1]
        self.__train_weights(training)
        errors = 0.0
        for i in range(test.size()):
            output = self.get_output(test.get(i))
            target = test.get(i).target
            error = False
            for j in range(len(output)):
                if math.fabs(float(output[j]) - float(target[j])) > margin:
                    error = True
            if error:
                errors += 1.0
        return 1.0 - (errors / test.size())

    def get_accuracy(self, k=10, margin=0.5):
        # @type data_set: InputSet
        folds = self.__data_set.split_folds(k)
        mean_accuracy = 0.0
        for i, validation_subset in enumerate(folds):
            training_indexes = []
            for j in range(len(folds)):
                if j != i:
                    training_indexes.extend(folds[j].get_data())
            training_subset = InputSubSet(training_indexes, self.__data_set)
            self.__train_weights(training_subset)
            errors = 0.0
            for j in range(validation_subset.size()):
                output = self.get_output(validation_subset.get(j))
                target = validation_subset.get(j).target
                error = False
                for i in range(len(output)):
                    if math.fabs(float(output[i]) - float(target[i])) > margin:
                        error = True
                if error:
                    errors += 1.0
            mean_accuracy +=  1.0 - (errors / validation_subset.size())
        return mean_accuracy / len(folds)

    def get_mse(self, k=10):
        # @type data_set: InputSet
        folds = self.__data_set.split_folds(k)
        mean_error = 0.0
        for i, validation_subset in enumerate(folds):
            training_indexes = []
            for j in range(len(folds)):
                if j != i:
                    training_indexes.extend(folds[j].get_data())
            training_subset = InputSubSet(training_indexes, self.__data_set)
            self.__train_weights(training_subset)
            sum_error = 0.0
            for j in range(validation_subset.size()):
                output = self.get_output(validation_subset.get(j))
                target = validation_subset.get(j).target
                error = 0.0
                for i in range(len(output)):
                    error += numpy.power(float(output[i]) - float(target[i]), 2)
                sum_error += error
            mean_error +=  sum_error / validation_subset.size()
        return mean_error / len(folds)

    def get_training_mse(self):
        """
        TODO Rename to get_test_mse
        """
        subsets = self.__data_set.split(int(self.__data_set.size()*0.75))
        training = subsets[0]
        test = subsets[1]
        self.__train_weights(training)
        sum_error = 0.0
        for i in range(test.size()):
            output = self.get_output(test.get(i))
            target = test.get(i).target
            error = 0.0
            for j in range(len(output)):
                error += numpy.power(float(output[j]) - float(target[j]), 2)
            sum_error += error
        return sum_error / test.size()

    def get_training_nrms(self):
        """
        TODO Rename to get_test_nrms
        """
        subsets = self.__data_set.split(int(self.__data_set.size()*0.75))
        training = subsets[0]
        test = subsets[1]
        self.__train_weights(training)
        sum_error = 0.0
        x_max = None
        x_min = None
        for i in range(test.size()):
            output = self.get_output(test.get(i))
            target = test.get(i).target
            error = 0.0
            for j in range(len(output)):
                error += numpy.power(float(output[j]) - float(target[j]), 2)
                if not x_max:
                    if float(output[j]) > float(target[j]):
                        x_max = float(output[j])
                    else:
                        x_max = float(target[j])
                else:
                    if float(output[j]) > float(target[j]):
                        if float(output[j]) > x_max:
                            x_max = float(output[j])
                    else:
                        if float(target[j]) > x_max:
                            x_max = float(target[j])
                if not x_min:
                    if float(output[j]) < float(target[j]):
                        x_min = float(output[j])
                    else:
                        x_min = float(target[j])
                else:
                    if float(output[j]) < float(target[j]):
                        if float(output[j]) < x_min:
                            x_min = float(output[j])
                    else:
                        if float(target[j]) < x_min:
                            x_min = float(target[j])
            sum_error += error
        mse = sum_error / test.size()
        rms = numpy.sqrt(mse)
        return rms/(x_max-x_min)

if __name__ == "__main__":

    data_set = InputSet()
    data_set.load("../data/servo.data")

    #<<ID: 487; SCORE: 0.20303 [{q:0.937668}{h:17}{c:144,54,41,81,85,52,140,67,48,138,95,110,6,32,5,86,22}{gamma:0.996954,2.48103,0.602891,3,1.42868,0.0979053,3,1.21504,0.922433,0.357251,0.131358,1.23423,0,0,0.299883,0.263622,1.9044}{lambda:0.0446531}]>>
    #centers = [144,54,41,81,85,52,140,68,48,138,95,110,6,32,5,86,22]
    #gammas = [0.996954,2.48103,1.602891,3,1.42868,0.0979053,3,1.21504,0.922433,0.357251,0.131358,1.23423,0,0,0.299883,0.263622,1.9044]
    #q = 0.937668
    #l = 0.0446531
    #hnn3 = HNN3(data_set, centers, gammas, q, l, "cls")
    #print str(hnn3.get_accuracy()*100) + "%"

    #<<ID: 28724; SCORE: 0.180124 [{q:0.254867}{h:41}{c:33,104,136,22,30,83,0,138,12,63,130,17,10,147,18,42,139,152,71,31,45,140,124,109,59,13,20,27,102,1,68,97,132,129,149,34,85,123,87,116,134}{gamma:0.963652,1.22752,0.502414,2.06288,0.957675,0.527096,2.29231,2.58408,0.419801,1.09144,0.742667,0.613447,0.301913,1.21125,0.695696,2.16505,0.0783844,0.550067,1.94488,0.679182,1.83098,0.42336,2.02004,0.700278,0.938683,1.02612,2.87757,0.962745,1.6509,0.88908,2.14539,0.078447,0.064547,1.38313,0.0152284,1.5391,0.87585,0.50174,2.01498,0.384209,1.39222}{lambda:0.140671}]>>
    #centers2 = [33,104,136,22,30,83,0,138,12,63,130,17,10,147,18,42,139,152,71,31,45,140,124,109,59,13,20,27,102,1,68,97,132,129,149,34,85,123,87,116,134]
    #gammas2 = [0.963652,1.22752,0.502414,2.06288,0.957675,0.527096,2.29231,2.58408,0.419801,1.09144,0.742667,0.613447,0.301913,1.21125,0.695696,2.16505,0.0783844,0.550067,1.94488,0.679182,1.83098,0.42336,2.02004,0.700278,0.938683,1.02612,2.87757,0.962745,1.6509,0.88908,2.14539,0.078447,0.064547,1.38313,0.0152284,1.5391,0.87585,0.50174,2.01498,0.384209,1.39222]
    #q2 = 0.254867
    #hnn3_2 = HNN3(data_set, centers2, gammas2, q2, "cls")
    #print str(hnn3_2.get_accuracy()*100) + "%"

    #<< ID: 5, SCORE: 0.98 { q: [0.80521102628186414] }  { lambda: [-1.0210171720290306] }  { h: [4] }  { centers: [39, 92, 93, 142] }  { gammas: [2.8276432116664818, 2.0996301169049274, 0.58572936354423788, 0.81636088316647271] } >>
    #centers = [39, 92, 93, 142]
    #gammas = [2.8276432116664818, 2.0996301169049274, 0.58572936354423788, 0.81636088316647271]
    #q = 0.80521102628186414
    #l = -1.0210171720290306
    #hnn3 = HNN3(data_set, centers, gammas, q, l, "cls")
    #print str(hnn3.get_accuracy()*100) + "%"

    #<< ID: None, SCORE: 0.987083333333 { q: [0.44220432726571074] }  { lambda: [0.96710920770657038] }  { h: [72] }  { centers: [18, 125, 154, 78, 106, 62, 52, 151, 124, 138, 46, 74, 70, 56, 82, 131, 118, 76, 132, 134, 108, 140, 112, 119, 90, 64, 5, 84, 19, 34, 45, 27, 50, 59, 99, 24, 42, 71, 14, 32, 79, 40, 75, 133, 2, 44, 113, 93, 114, 136, 43, 31, 51, 15, 135, 53, 48, 20, 122, 95, 98, 89, 33, 103, 26, 38, 149, 107, 147, 81, 29, 83] }  { gammas: [0.00079618240692724829, 2.5076106350854732, 2.1112335229282801, 0.73880781130930462, 0.31186446490157815, 0.16448094177401518, 2.4442478342445146, 0.33049777420279303, 1.5645360897670795, 1.7374999478964606, 1.7374199721708474, 1.7682856978748061, 2.3750487510380225, 1.3781217613352363, 2.3954738696702331, 2.8816592017154932, 1.6101326120915327, 1.6280050820269794, 1.2870450051510915, 0.68463472051687513, 0.35409619121995595, 0.36536858480521117, 1.9098069383596741, 0.15678561484729103, 0.60777186821468876, 0.99044143490928449, 1.8653736027293224, 0.026362579724533819, 1.0286322210310113, 1.3339364761013339, 1.4655135549425662, 1.0708537746303448, 1.0921311619114915, 1.9684986688600374, 0.28764970534840684, 0.75085758662874114, 0.67623565877174319, 0.41779523373227478, 2.4182766508743869, 1.7787970861216578, 2.3816797160255643, 2.7774656545892658, 1.2752536837051545, 2.2488540005093696, 2.1112439245490608, 0.35756157789516918, 2.519486953485889, 2.8279239639155112, 2.7342979617060759, 2.7575907085018998, 0.91266277331275392, 2.7187407254424842, 1.0825333553266108, 0.64095551481873869, 0.5033714108714753, 1.5332711000151282, 2.1694118674292429, 1.3396105657224553, 1.7338250319255999, 0.79292318377895854, 2.1299995230261177, 1.3367737200517, 2.8738341722478142, 1.5138402947321703, 2.3834870986680463, 0.41047539595062854, 2.5820095228305697, 1.6131789639812717, 1.8778350750518409, 1.9999027730572845, 2.1568541005964099, 2.2979090256623991] } >>
#    centers = [18, 125, 154, 78, 106, 62, 52, 151, 124, 138, 46, 74, 70, 56, 82, 131, 118, 76, 132, 134, 108, 140, 112, 119, 90, 64, 5, 84, 19, 34, 45, 27, 50, 59, 99, 24, 42, 71, 14, 32, 79, 40, 75, 133, 2, 44, 113, 93, 114, 136, 43, 31, 51, 15, 135, 53, 48, 20, 122, 95, 98, 89, 33, 103, 26, 38, 149, 107, 147, 81, 29, 83]
#    gammas = [0.00079618240692724829, 2.5076106350854732, 2.1112335229282801, 0.73880781130930462, 0.31186446490157815, 0.16448094177401518, 2.4442478342445146, 0.33049777420279303, 1.5645360897670795, 1.7374999478964606, 1.7374199721708474, 1.7682856978748061, 2.3750487510380225, 1.3781217613352363, 2.3954738696702331, 2.8816592017154932, 1.6101326120915327, 1.6280050820269794, 1.2870450051510915, 0.68463472051687513, 0.35409619121995595, 0.36536858480521117, 1.9098069383596741, 0.15678561484729103, 0.60777186821468876, 0.99044143490928449, 1.8653736027293224, 0.026362579724533819, 1.0286322210310113, 1.3339364761013339, 1.4655135549425662, 1.0708537746303448, 1.0921311619114915, 1.9684986688600374, 0.28764970534840684, 0.75085758662874114, 0.67623565877174319, 0.41779523373227478, 2.4182766508743869, 1.7787970861216578, 2.3816797160255643, 2.7774656545892658, 1.2752536837051545, 2.2488540005093696, 2.1112439245490608, 0.35756157789516918, 2.519486953485889, 2.8279239639155112, 2.7342979617060759, 2.7575907085018998, 0.91266277331275392, 2.7187407254424842, 1.0825333553266108, 0.64095551481873869, 0.5033714108714753, 1.5332711000151282, 2.1694118674292429, 1.3396105657224553, 1.7338250319255999, 0.79292318377895854, 2.1299995230261177, 1.3367737200517, 2.8738341722478142, 1.5138402947321703, 2.3834870986680463, 0.41047539595062854, 2.5820095228305697, 1.6131789639812717, 1.8778350750518409, 1.9999027730572845, 2.1568541005964099, 2.2979090256623991]
#    q = 0.44220432726571074
#    l = 0.96710920770657038
#    hnn3 = HNN3(data_set, centers, gammas, q, l, "cls")
#    print str(hnn3.get_accuracy()*100) + "%"

    #<< ID: None, SCORE: None { q: [-0.096545285695130545] }  { lambda: [1.9127189444943609] }  { h: [51] }  { centers: [27, 109, 61, 50, 56, 8, 53, 116, 141, 14, 64, 139, 71, 57, 5, 4, 86, 40, 140, 104, 130, 138, 9, 124, 107, 25, 21, 153, 144, 29, 1, 60, 136, 114, 145, 22, 45, 59, 129, 15, 49, 58, 96, 127, 142, 108, 47, 24, 16, 34, 147] }  { gammas: [1.8580964989204645, 0.81391955852591669, -0.24823838534650799, 3.0, -0.24378115373921905, 2.1286616124937634, 0.28152696564364277, 2.1082972614071105, 1.1703705206145747, -0.36832876436596385, 0.98967536389628497, 3.0, 1.1317047910051923, 2.1485912054344478, 3.0, 2.3847235516250742, 0.2385628473575685, 2.6574956301068591, 1.0399623376086513, 1.7649214394152648, 1.5778655566274744, 0.49197362240130915, 0.26621284129518508, 1.83421710473945, 2.3366585050945536, 1.0726035778866856, 1.6477021209867737, -0.35328440679216666, 0.353733807700785, 2.3565397385423408, 1.6376264880520235, 1.3114473775008308, 2.6717934279083844, 3.0, 1.6673724452339223, 2.809156367812609, 1.9749194992476204, -1.4472070044817873, 3.0, 2.0203361244151852, 2.2263754416360828, 0.82824197019612744, 2.8623695385921355, 6.5526181292963059e-05, 1.3965166808770753, 1.6643061809840805, 2.2093056734904599, 0.47987829393648224, 2.6373008476849424, 1.4238826567127898, 1.2397140048706881] } >>
    centers = [27, 109, 61, 50, 56 ]
    gammas = [1.8580964989204645, 0.81391955852591669, -0.24823838534650799, -0.24378115373921905, 2.1286616124937634]
    q = -0.096545285695130545
    l = 1.9127189444943609
    hnn3 = HNN3(data_set, centers, gammas, q, l)
    print str(hnn3.get_training_nrms())

    exit(0)
