
class GetPrompts():
    def __init__(self):
        self.prompt_task = ("Act as a professional algorithm designer. "
                            "Design a heuristic for a warehouse optimization problem to minimize the number of reshuffling moves needed to reach a blockage-free state. "
                            "If a unit load of a lower priority class hinders access to a unit load of a higher priority class it is deemed blocking. "
                            "The heuristic should score each warehouse state. "
                            "Only the warehouse state with the highest score is selected in a tree search procedure. "
                            )
        self.prompt_func_name = "select_next_move"
        self.prompt_func_inputs = ["warehouse_states"]
        self.prompt_func_outputs = ["scores"]
        self.prompt_inout_inf = ("'warehouse_states' is the size of all potential warehouse states after all potential reshuffling moves. "
                                 "The output named 'scores' is the scores for the warehouse states. ")
        self.prompt_other_inf = ("Note that 'warehouse_states' is a three levels nested list with integers in the third level sublist. "
                                 "'scores' must be a list of integers or floats. "
                                 "Avoid utilizing the random component, and it is crucial to maintain self-consistency. "
                                 "Do not give additional explanations. "
                                 "Don't create additional methods and please avoid nesting methods. "
                                 )
        self.prompt_example = ("'warehouse_states' is represented by a three levels deep nested list."
                               "The second level list represents a warehouse state as a list of lists. "
                               "The third level list represents a lane of unit loads as a list of integers. "
                               "The first list index (index 0) is the outermost slot in the lane. "
                               "The highest list index is the innermost slot in the lane. "
                               "Lanes are accessed from the first index to the highest index. "
                               "Each integer represents a unit load and its priority class. "
                               "Unit load of the same priority class are equal. "
                               "A 1 represents the highest priority class. "
                               "A 5 represents the lowest priority class. "
                               "A 3 represents a priority class lower than 1 but higher than 5. "
                               "A 4 represents a priority class lower than 3 but higher than 5. "
                               "A 0 represents an empty slot. "
                               "Each lane must have all 0s (empty slots) grouped at the start or have no 0s at all, "
                               "ensuring that if any non-zero elements appear in a lane, all subsequent slots must also be non-zero. "
                               "Therefore, impossible configurations are: "
                               "[1, 1, 0, 0] or [2,0,2], "
                               "while possible configurations are:"
                               " [0, 0, 1, 2] or [1, 2, 3, 3]. "
                               "\n "
                               "Examples for blocking unit loads: "
                               "In the lane [0, 4, 1] the 4 blocks access to 1. "
                               "In the lane [3, 3, 2] the two 3s block access to the 2. "
                               "In the lane [0, 5, 1, 5, 2] the two 5s block access to the 2 and 1. "
                               "In the lane [0, 4, 4, 3] the two 4s block access to the 3. "
                               "\n "
                               "First example for 'warehouse_states': "
                               "["
                               "[[0, 2, 3], [0, 5, 5], [5, 1, 1]], "
                               "[[0, 2, 3], [5, 5, 5], [0, 1, 1]], "
                               "[[5, 2, 3], [1, 5, 5], [0, 0, 1]],"
                               "] "
                               "Second example for 'warehouse_states': "
                               "["
                               "[[2, 2, 3, 5], [0, 3, 5, 4], [0, 0, 2, 2]], "
                               "[[0, 0, 3, 5], [2, 3, 5, 4], [0, 2, 2, 2]], "
                               "[[0, 2, 3, 5], [0, 0, 5, 4], [3, 2, 2, 2]], "
                               "[[0, 0, 3, 5], [0, 3, 5, 4], [2, 2, 2, 2]],"
                               "] "
                               "\n "
                               "First example for 'scores': "
                               "[0, 1, 3]"
                               "Second example for 'scores': "
                               "[-3, -1, -4] "
                               )

    def get_task(self):
        return self.prompt_task
    
    def get_func_name(self):
        return self.prompt_func_name
    
    def get_func_inputs(self):
        return self.prompt_func_inputs
    
    def get_func_outputs(self):
        return self.prompt_func_outputs
    
    def get_inout_inf(self):
        return self.prompt_inout_inf

    def get_other_inf(self):
        return self.prompt_other_inf

    def get_examples(self):
        return self.prompt_example

if __name__ == "__main__":
    getprompts = GetPrompts()
    print(getprompts.get_task())
