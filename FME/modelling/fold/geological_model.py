from FME.modelling.geological_points import GPoint, IPoint
class GeologicalModel:
    """
    A geological model is the recipe for building a 3D model and includes the
    """
    def __init__(self):
        self.features = {}
        self.data = {}
        self.data['gradient'] = []
        self.data['value'] = []
    def add_data(self,data):
        if type(data) == IPoint:
            self.data['value'].append(data)
        if type(data) == GPoint:
            self.data['gradient'].append(data)
    def add_feature(self,feature):
