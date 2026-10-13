import re
from ...llm.interface_LLM import InterfaceLLM


class Evolution():

    def __init__(self, paras, prompts, **kwargs):

        # set prompt interface
        # getprompts = GetPrompts()
        self.llm_temperature = paras.llm_temperature
        self.prompt_task = prompts.get_task()
        self.prompt_func_name = prompts.get_func_name()
        self.prompt_func_inputs = prompts.get_func_inputs()
        self.prompt_func_outputs = prompts.get_func_outputs()
        self.prompt_inout_inf = prompts.get_inout_inf()
        self.prompt_other_inf = prompts.get_other_inf()
        self.prompt_example = prompts.get_examples()


        self.use_example = paras.ec_use_example
        self.use_idea = paras.ec_use_idea
        self.use_math_model = paras.ec_use_math_model
        if self.use_math_model:
            self.prompt_math_model = prompts.get_math_model()
        else:
            self.prompt_math_model = ""

        self.llm_url_info = paras.llm_url_info

        if len(self.prompt_func_inputs) > 1:
            self.joined_inputs = ", ".join("'" + s + "'" for s in self.prompt_func_inputs)
        else:
            self.joined_inputs = "'" + self.prompt_func_inputs[0] + "'"

        if len(self.prompt_func_outputs) > 1:
            self.joined_outputs = ", ".join("'" + s + "'" for s in self.prompt_func_outputs)
        else:
            self.joined_outputs = "'" + self.prompt_func_outputs[0] + "'"

        # set LLMs
        self.api_endpoint = paras.llm_api_endpoint
        self.api_key = paras.llm_api_key
        self.model_LLM = paras.llm_model
        self.debug_mode = paras.exp_debug_mode  # close prompt checking

        self.interface_llm = InterfaceLLM(paras)

    def get_prompt_ideas(self, ideas):
        ideas_content = ""
        for i, indiv in enumerate(ideas):
            ideas_content += (
                "\n "
                f"No. {i + 1} idea details are: \n"
                f"Idea Name: {indiv['Idea Name']}\n"
                f"Logic: {indiv['Logic']}\n"
                f"Implementation: {indiv['Implementation']}\n"
            )
        return ideas_content

    def get_prompt_i1(self):

        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += f"\n" + self.prompt_example

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        if self.use_example:
            prompt_content += (f"\n"
                               f"First, understand the provided problem description and input and output examples. "
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += f"Third, "
        else:
            prompt_content += (f"\n"
                               f"First, ")

        prompt_content += (f"describe your new algorithm and main steps in one sentence. "
                           f"The description must be inside a brace. "
                           f"\n "
                           f"Next, implement it in Python as a function named {self.prompt_func_name}. "
                           f"This function should accept {str(len(self.prompt_func_inputs))} input(s): {self.joined_inputs }. "
                           f"The function should return {str(len(self.prompt_func_outputs))} output(s): {self.joined_outputs}. "
                           f"{self.prompt_inout_inf} {self.prompt_other_inf} \n"
                           f"Do not give additional explanations. "
                           f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."
                           )
        return prompt_content


    def get_prompt_e1(self, indivs):
        prompt_indiv = ""
        for i, indiv in enumerate(indivs):
            prompt_indiv += (
                f"No. {i + 1} algorithm and the corresponding code are: \n"
                f"{indiv['algorithm']} \n{indiv['code']} \n"
            )

        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += "\n" + self.prompt_example

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        prompt_content += (
            f"\nI have {len(indivs)} existing algorithms with their codes as follows: \n{prompt_indiv}"
            f"Please help me create a new algorithm that has a totally different form from the given ones. ")

        if self.use_example:
            prompt_content += (f"\n"
                               f"First, understand the provided problem description, input, and output examples. "
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += f"Third, "
        else:
            prompt_content += (f"\n"
                               f"First, ")
        prompt_content += (
            f"describe your new algorithm and main steps in one sentence. The description must be inside a brace. "
            f"\n "
            f"Next, implement it in Python as a function named {self.prompt_func_name}. "
            f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
            f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
            f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
            f"Do not give additional explanations. "
            f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."

        )
        return prompt_content

    def get_prompt_e2(self, indivs):
        prompt_indiv = "".join(
            f"No. {i + 1} algorithm and the corresponding code are: \n{indiv['algorithm']} \n{indiv['code']} \n"
            for i, indiv in enumerate(indivs)
        )

        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += (f"\n{self.prompt_example}")

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        prompt_content += (
            f"\n I have {len(indivs)} existing algorithms with their codes as follows: \n{prompt_indiv}"
            f"Please help me create a new algorithm that has a totally different form from the given ones but can be motivated from them. ")

        if self.use_example:
            prompt_content += (f"\n"
                               f"First, understand the provided problem description, input, and output examples. "
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += (f"Third, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Fourth, ")
        else:
            prompt_content += (f"\n"
                               f"First, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Second, ")

        prompt_content += (
            f"based on the backbone idea, describe your new algorithm in one sentence. "
            f"The description must be inside a brace. "
            f"\n "
            f"Next, implement it in Python as a function named {self.prompt_func_name}. "
            f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
            f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
            f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
            f"Do not give additional explanations. "
            f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."

        )
        return prompt_content

    def get_prompt_m1(self, indiv1):
        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += f"\n{self.prompt_example}"

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        prompt_content += (
            f"\nI have one algorithm with its code as follows:\n"
            f"Algorithm description: {indiv1['algorithm']}\n"
            f"Code:\n{indiv1['code']}\n"
            f"Please assist me in creating a new algorithm that has a different form but can be a modified version of the algorithm provided.\n"
        )

        if self.use_example:
            prompt_content += (f"\n"
                               f"First, understand the provided problem description, input, and output examples. "
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += (f"Third, "
                               )
        else:
            prompt_content += (f"\n"
                               f"First, ")

        prompt_content += (
            f"describe your new algorithm and main steps in one sentence. The description must be inside a brace. "
            f"\n "
            f"Next, implement it in Python as a function named {self.prompt_func_name}. "
            f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
            f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
            f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
            f"Do not give additional explanations. "
            f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."
        )
        return prompt_content

    def get_prompt_m2(self, indiv1):
        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += f"\n{self.prompt_example}"

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        prompt_content += (
            f"\nI have one algorithm with its code as follows:\n"
            f"Algorithm description: {indiv1['algorithm']}\n"
            f"Code:\n{indiv1['code']}\n"
            f"Please identify the main algorithm parameters and assist me in creating a new algorithm that has different parameter settings for the score function provided.\n")

        if self.use_example:
            prompt_content += (f"\n"
                               f"First, understand the provided problem description, input, and output examples. "
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += (f"Third, "
                               )
        else:
            prompt_content += (f"\n"
                               f"First, ")

        prompt_content += (
            f"describe your new algorithm and main steps in one sentence. The description must be inside a brace. "
            f"\n "
            f"Next, implement it in Python as a function named {self.prompt_func_name}. "
            f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
            f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
            f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
            f"Do not give additional explanations. "
            f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."

        )
        return prompt_content

    def get_prompt_m3(self, indiv1):
        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += f"\n{self.prompt_example}"

        if self.use_math_model:
            prompt_content += "\n " + self.prompt_math_model

        if self.use_example:
            prompt_content += ("\n"
                               "First, understand the provided problem description, input, and output examples. "
                               "Then extract the main constraints of the problem. "
                               "Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += ("Third, "
                               )
        else:
            prompt_content += (f"\n"
                               f"First, ")

        prompt_content += (
            f"you need to identify the main components in the function below. "
            f"Next, analyze whether any of these components can be overfit to the in-distribution instances. "
            f"Then, based on your analysis, simplify the components to enhance the generalization to potential out-of-distribution instances. "
            f"Finally, provide the revised code, keeping the function name, inputs, and outputs unchanged.\n"
            f"{indiv1['code']}\n"
            f"{self.prompt_inout_inf}\n"
            f"Do not give additional explanations. "
            f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."
        )
        return prompt_content

    def get_prompt_p0(self, ideas):

        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += (f"\n{self.prompt_example}")

        prompt_content += "I have some ideas to design a new heuristic: \n"
        prompt_content += self.get_prompt_ideas(ideas)
        prompt_content += ""

        prompt_content += "Please help me create a new algorithm. "
        prompt_content += "The new algorithm should also be inspired by the provided ideas. "

        if self.use_example:
            prompt_content += (f"\n"
                               f'First, understand the provided problem description, input, and output examples. '
                               f"Then extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += (f"Third, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Fourth, ")
        else:
            prompt_content += (f"\n"
                               f"First, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Second, ")

        prompt_content += (
                f"based on the backbone idea, describe your new algorithm in one sentence. "
                f"The description must be inside a brace. "
                f"\n "
                f"Next, implement it in Python as a function named {self.prompt_func_name}. "
                f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
                f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
                f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
                f"Do not give additional explanations. "
                f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."

        )
        return prompt_content

    def get_prompt_p1(self, indivs, ideas):
        prompt_indiv = "".join(
            f"No. {i + 1} algorithm and the corresponding code are: \n{indiv['algorithm']} \n{indiv['code']} \n"
            for i, indiv in enumerate(indivs)
        )

        prompt_content = self.prompt_task

        if self.use_example:
            prompt_content += (f"\n{self.prompt_example}")

        prompt_content += "Here are some ideas to design a new heuristic: \n"
        prompt_content += self.get_prompt_ideas(ideas)
        prompt_content += ""

        prompt_content += (
                f"\n I have {len(indivs)} existing algorithms with their codes as follows: \n{prompt_indiv}")

        prompt_content += "Please help me create a new algorithm that enriches the given algorithms with the new ideas provided. "

        if self.use_example:
            prompt_content += (f"\n"
                               f'First, understand the provided problem description, input, and output examples. '
                               f"Than extract the main constraints of the problem. "
                               f"Second, think about how these constraints affect the requested heuristic. "
                               )
            prompt_content += (f"Third, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Fourth, ")
        else:
            prompt_content += (f"\n"
                               f"First, "
                               f"identify the common backbone idea in the provided algorithms. "
                               f"Second, ")

        prompt_content += (
                f"based on the backbone ideas, describe your new algorithm in one sentence. "
                f"The description must be inside a brace. "
                f"\n "
                f"Next, implement it in Python as a function named {self.prompt_func_name}. "
                f"This function should accept {len(self.prompt_func_inputs)} input(s): {self.joined_inputs}. "
                f"The function should return {len(self.prompt_func_outputs)} output(s): {self.joined_outputs}. "
                f"{self.prompt_inout_inf} {self.prompt_other_inf}\n"
                f"Do not give additional explanations. "
                f"Remember: Describe your new algorithm and main steps in one sentence inside a brace and implement the algorithm in Python as a function."
        )
        return prompt_content

    def _get_alg(self, prompt_content):

        response, full_response = self.interface_llm.get_response(prompt_content)

        algorithm = re.findall(r"\{(.*)\}", response, re.DOTALL)
        if len(algorithm) == 0:
            if 'python' in response:
                algorithm = re.findall(r'^.*?(?=python)', response, re.DOTALL)
            elif 'import' in response:
                algorithm = re.findall(r'^.*?(?=import)', response, re.DOTALL)
            else:
                algorithm = re.findall(r'^.*?(?=def)', response, re.DOTALL)

        code = re.findall(r"import.*return", response, re.DOTALL)
        if len(code) == 0:
            code = re.findall(r"def.*return", response, re.DOTALL)

        n_retry = 1
        while (len(algorithm) == 0 or len(code) == 0):
            if self.debug_mode:
                print("Error: algorithm or code not identified, wait 1 seconds and retrying ... ")

            response, full_response = self.interface_llm.get_response(prompt_content)

            algorithm = re.findall(r"\{(.*)\}", response, re.DOTALL)
            if len(algorithm) == 0:
                if 'python' in response:
                    algorithm = re.findall(r'^.*?(?=python)', response, re.DOTALL)
                elif 'import' in response:
                    algorithm = re.findall(r'^.*?(?=import)', response, re.DOTALL)
                else:
                    algorithm = re.findall(r'^.*?(?=def)', response, re.DOTALL)

            code = re.findall(r"import.*return", response, re.DOTALL)
            if len(code) == 0:
                code = re.findall(r"def.*return", response, re.DOTALL)

            if n_retry > 3:
                break
            n_retry += 1

        algorithm = algorithm[0]
        code = code[0]

        # Check if the variable is used
        match_ret_val = re.search(r'return\s+([a-zA-Z_][a-zA-Z_0-9]*)', response)

        # If None, the Expression is in return statement
        if match_ret_val is None:
            match_ret_val = re.search(r'return\s+(.+)', response)

        code_all = code+" "+f" {match_ret_val.group(1)}"

        return [code_all, algorithm], full_response

    def i1(self):

        prompt_content = self.get_prompt_i1()

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ i1 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def e1(self, parents):

        prompt_content = self.get_prompt_e1(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ e1 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def e2(self, parents):

        prompt_content = self.get_prompt_e2(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ e2 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def m1(self, parents):

        prompt_content = self.get_prompt_m1(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m1 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def m2(self, parents):

        prompt_content = self.get_prompt_m2(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m2 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def m3(self, parents):

        prompt_content = self.get_prompt_m3(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m3 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def p1(self, parents, ideas):

        prompt_content = self.get_prompt_p1(parents,ideas)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ p1 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

    def p0(self, ideas):

        prompt_content = self.get_prompt_p0(ideas)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ p0 ] : \n", prompt_content)
            print(">>> Press 'Enter' to continue")
            input()

        [code_all, algorithm], full_response = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm], prompt_content, full_response

