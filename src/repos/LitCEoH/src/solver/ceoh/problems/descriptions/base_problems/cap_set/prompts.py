
class GetPrompts():
    def __init__(self):
        self.prompt_task = ("I need help designing a novel score function select elements for the capset problem."
                            "n each step, the vector with the highest score is added to the capset, penalizing those "
                            "that reduce future options, so that we ultimately build a large set avoiding three-term arithmetic progressions"
                            "The final goal is to find most dimensions, which solve the capset problem."
                            )
        self.prompt_func_name = "select_next_element"
        self.prompt_func_inputs = ["elements", "dimension"]
        self.prompt_func_outputs = ["scores"]
        self.prompt_inout_inf = ("Returns the priority with which we want to add `element` to the cap set.")
        self.prompt_other_inf = ""
        self.prompt_example = ""

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
