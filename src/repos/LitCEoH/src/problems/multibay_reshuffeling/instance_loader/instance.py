import sys
import os
wd = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(wd, '../..'))

from bay.warehouse import Warehouse
from instance.instance_loader import InstanceLoader
from examples_gen.unit_load import UnitLoad
from examples_gen.unit_load_gen import UnitLoadGenerator
import numpy as np
import json

class Instance(): 
    """
    Instance class object that handles all objects related to an instance and can 
    be created by either passing an instanceLoader object, which requires an instance 
    json file as input or by manually setting all the variables but instanceLoader.
    
    This class is able to describe instances that work with a max priority class and 
    with unit loads that have to be retrieved within a time window.
    To differentiate between the two, the max_p variable is used. If max_p is set to 0, 
    the instance is assumed to be a BRR instance with time windows,
    otherwise it is assumed to be a CP instance with a max priority class.
    """
    def __init__(self, 
                 instanceLoader: InstanceLoader=None, 
                 layout_file: str=None, 
                 fill_level: float=None, 
                 max_p: int=None,
                 height: int=None,
                 seed: int=None,
                 access_directions: dict=None,
                 exampleGenerator = None,
                 ): 
        try: 
            if instanceLoader is not None: 
                self.layout_file = instanceLoader.get_layout_filename()
                self.fill_level = instanceLoader.get_fill_level()
                self.max_p = instanceLoader.get_max_p()
                self.height = instanceLoader.get_height()
                self.seed = instanceLoader.get_seed()
                self.access_directions = instanceLoader.get_access_directions()
                self.sink = instanceLoader.get_sink()
                self.source = instanceLoader.get_source()
                self._build_warehouse()
                self.unit_loads = []
                self._populate_slots(instanceLoader=instanceLoader)
            else: 
                self.layout_file = layout_file 
                self.fill_level = fill_level
                self.max_p = max_p
                self.height = height
                self.seed = seed
                self.access_directions = access_directions
                self._build_warehouse()
                self.sink = self.wh_initial.has_sinks()
                self.source = self.wh_initial.has_sources()
                self.unit_loads = [] # stays empty when working with priorities
                self._populate_slots(exampleGenerator=exampleGenerator)
            if self.wh_initial.has_sinks(): 
                self._check_feasibility_for_sinks()
            if self.wh_initial.has_sources():
                self._check_feasibility_for_sources()
            if len(self.unit_loads) > 0:
                self._check_feasibility_for_unit_loads()


        except TypeError as e: 
            print("Error: Make sure that you fully describe the instance by either using the instanceLoader \n or setting all of the other parameters when creating an object of the instance class.")
            print(e.args)
            sys.exit(1)

    def __str__(self): 
        return str({
            "layout_file": self.layout_file,
            "access_directions": self.access_directions, 
            "sink": self.sink,
            "source": self.source,
            "seed": self.seed, 
            "height": self.height, 
            "max_p": self.max_p, 
            "fill_level": self.fill_level, 
            "unit_loads": len(self.unit_loads),
        })

    
    def _build_warehouse(self):
        self.wh_initial = Warehouse(self.layout_file, self.access_directions) 
        self.wh_reshuffled = Warehouse(self.layout_file, self.access_directions) 

    def _populate_slots(self, instanceLoader: InstanceLoader=None, exampleGenerator=None): 
        if instanceLoader is None and exampleGenerator is None: 
            print("Error: Warehouse could not be populated. Either pass an instanceLoader or \n exampleGenerator to the Instance Constructor.")
            sys.exit(1)
        if instanceLoader is not None: 
            if instanceLoader.get_unit_loads(): 
                self.unit_loads = self._create_unit_loads(instanceLoader.get_unit_loads())
            else: 
                self.unit_loads = []
                instanceLoader.generate_bays_priorities(self.wh_initial.bays, height=self.height)
        elif exampleGenerator is not None: 
            self.unit_loads = exampleGenerator.generate_bays_priorities(self.wh_initial.bays, height=self.height)
        self.fill_level = self.wh_initial.estimate_fill_level()

    def _create_unit_loads(self, unit_loads):
        """
        Creates unit loads from the unit load dictionary in the instance file
        """
        unit_loads_list = []
        for ul in unit_loads: 
            unit_loads_list.append(UnitLoad(id=ul["id"], retrieval_start=ul["retrieval_start"], retrieval_end=ul["retrieval_end"], arrival_start=ul["arrival_start"], arrival_end=ul["arrival_end"]))
        return unit_loads_list

    def _check_feasibility_for_sinks(self): 
        """
        Searches all bays if atleast 1 item per priority class is present - this is required 
        for the Block Relocation Problem aka the problem with a sink
        """
        items = []
        for bay in self.wh_initial.bays: 
            items.append(bay.state.ravel())
        for priority in range(1, self.max_p +1): 
            exists = False
            for array in items:
                if np.any(array == priority):
                    exists = True
                    break
            if not exists:
                print(f"This instance is not feasible for the block relocation problem, as there is no item of priority {priority}:")
                print(self)
                sys.exit(1)

    def _check_feasibility_for_sources(self):
        if not self.wh_initial.has_sinks():
            print(f"A layout cannot contain a source without a corresponding sink:")
            print(self)
            sys.exit(1)

    def _check_feasibility_for_unit_loads(self):
        """
        Checks if the unit load ids are unique
        """
        ids = []
        for ul in self.unit_loads: 
            ids.append(ul.id)
        if len(ids) != len(set(ids)):
            print(f"Error: The unit load ids are not unique:")
            print(self)
            sys.exit(1)

    def get_access_directions(self):
        return self.access_directions
    
    def get_layout_file(self): 
        return self.layout_file

    def get_filename(self):
        return self.layout_file.split("/")[-1].split(".")[0]

    def get_fill_level(self): 
        return self.fill_level

    def get_max_p(self):
        return self.max_p
    
    def get_height(self):
        return self.height
    
    def get_seed(self):
        return self.seed
    
    def has_sink(self):
        return self.sink
    
    def has_source(self):
        return self.source

    def get_warehouse(self): 
        return

    def save_instance(self, filename): 
        """
        Saves the instance as a json file.
        """
        data = dict()
        data['layout_file'] = self.get_layout_file()
        data['fill_level'] = self.get_fill_level()
        data['max_priority'] = self.get_max_p()
        data['height'] = self.get_height()
        data['seed'] = self.get_seed()
        data['sink'] = self.has_sink()
        data['source'] = self.has_source()

        data['bay_info'] = dict()
        data['sink_info'] = dict()
        data['source_info'] = dict()
        data['initial_state'] = dict()
        for bay in self.wh_initial.bays:
            data['bay_info'][bay.get_id()] = bay.to_data_dict()
            data['initial_state'][bay.get_id()] = bay.state.tolist()
    
        for sink in self.wh_initial.sinks: 
            data['sink_info'][sink.get_id()] = sink.to_data_dict()

        for source in self.wh_initial.sources: 
            data['source_info'][source.get_id()] = source.to_data_dict()

        data['access_points'] = []
        for point in self.wh_initial.all_access_points:
            data['access_points'].append(point.to_data_dict())

        data['unit_loads'] = []
        if self.max_p == 0: 
            for ul in self.unit_loads:
                data['unit_loads'].append(ul.to_data_dict()) 

        f = open(filename, 'w')
        json.dump(data, f, indent=4)
        f.close()


if __name__ == '__main__': 
    from examples_gen.lane_stack_gen import LanedStackGen

    # Test instance generator with priorities
    instance2 = Instance(
        layout_file="examples/Size_3x3_Layout_3x3_sink_source.csv",
        fill_level=0.8,
        max_p=4,
        height=1,
        seed=1,
        access_directions={"north": True, "east": True, "south": True, "west": True}, 
        exampleGenerator=LanedStackGen(max_priority=4, fill_level=0.7, seed=1), 
    )
    print(f"Generated Instance: {instance2}")
    instance2.save_instance("experiments/test2.json")

    # Test instance loader with priorities
    instance = Instance(InstanceLoader("experiments/test2.json"))
    print(f"InstanceLoader: {instance}")
    instance.save_instance("experiments/test3.json")

    # Test instance generator with unit loads
    instance3 = Instance(
        layout_file="examples/Size_3x3_Layout_2x2_sink_source.csv",
        fill_level=0.8,
        max_p=0,
        height=1,
        seed=1,
        access_directions={"north": True, "east": True, "south": True, "west": True}, 
        exampleGenerator=UnitLoadGenerator(tw_length=15, fill_level=0.8, seed=1),
    )
    print(f"Generated Instance: {instance3}")
    instance3.save_instance("experiments/test.json")

    # Test instance loader with unit loads
    instance4 = Instance(InstanceLoader("experiments/test.json"))
    print(f"InstanceLoader: {instance4}")