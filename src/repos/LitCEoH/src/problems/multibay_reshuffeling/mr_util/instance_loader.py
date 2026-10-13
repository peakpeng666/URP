class InstanceLoader(): 
    def __init__(self, instance): 
        self.n = 1
        self.file = instance["layout_file"].split("/")[-1].split(".")[0]
        self.fill_level = instance["fill_level"]
        self.max_priority = instance["max_priority"]
        self.height = instance["height"]
        self.seed = instance["seed"]
        self.access_directions = self._create_access_directions_dict(instance["bay_info"]["0"]["access_directions"])

    def _create_access_directions_dict(self, access_directions): 
        north, east, south, west = False, False, False, False
        if "north" in access_directions: 
            north = True
        if "east" in access_directions: 
            east = True
        if "south" in access_directions: 
            south = True
        if "west" in access_directions: 
            west = True
        return {
            "north": north, 
            "east" : east,
            "south": south,
            "west" : west
        }