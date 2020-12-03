from abc import ABC


class RawInput:
    def __init__(self, object, config)

class Processor(ABC):
    def __init__(self, input, output):
        self.input = input
        self.output = output
        self.config = config

    @abc.abstractproperty
    def process(self):
        pass


class Beamformer(Processor):
    def __init__(self, input, weights, output):
        super(Beamformer, self).__init__(input, output, config)
        self.weights = weights

    def process(self):
        pass
