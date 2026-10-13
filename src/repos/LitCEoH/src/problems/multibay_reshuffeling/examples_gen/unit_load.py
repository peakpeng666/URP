class UnitLoad(): 
    def __init__(self, 
                 id, 
                 retrieval_start: int=None, 
                 retrieval_end: int=None, 
                 arrival_start: int=None, 
                 arrival_end: int=None): 
        """
        In the variant without a source, the arrival_start and arrival_end are always None. 
        Time is modeled in discrete time steps as integers.
        """
        self.id = id
        self.retrieval_start = retrieval_start
        self.retrieval_end = retrieval_end
        self.arrival_start = arrival_start
        self.arrival_end = arrival_end
        self.retrieved = False
        # check if the unit load is already stored in the warehouse
        if arrival_start is not None and arrival_start > 0:
            self.stored = False
        else:
            self.stored = True
        self._feasibility_checks()


    def __str__(self) -> str:
        return f"UnitLoad {self.id}, retrieval: {self.retrieval_start} - {self.retrieval_end}, arrival: {self.arrival_start} - {self.arrival_end}"
    
    def _feasibility_checks(self):
        if self.retrieval_start is None: 
            raise ValueError("retrieval_start must be set")
        if self.retrieval_end is None: 
            raise ValueError("retrieval_end must be set")
        if self.retrieval_end < self.retrieval_start: 
            raise ValueError("retrieval_end must be greater than retrieval_start")
        if self.arrival_start is not None:
            if self.arrival_end is None:
                raise ValueError("arrival_end must be set if arrival_start is set")
            if self.arrival_end <= self.arrival_start:
                raise ValueError("arrival_end must be greater than arrival_start")
            if self.arrival_end > self.retrieval_start:
                raise ValueError("arrival_end must be smaller than retrieval_start")
        

    def retrieve(self): 
        if self.stored is False:
            raise ValueError("unit load must be stored to retrieve it")
        self.retrieved = True
        self.stored = False

    def store(self):
        if self.arrival_start is None:
            raise ValueError("arrival_start must be set to store the unit load")
        self.retrieved = False
        self.stored = True

    def to_data_dict(self): 
        data = dict()
        data['id'] = self.id
        data['retrieval_start'] = self.retrieval_start
        data['retrieval_end'] = self.retrieval_end
        data['arrival_start'] = self.arrival_start
        data['arrival_end'] = self.arrival_end
        return data