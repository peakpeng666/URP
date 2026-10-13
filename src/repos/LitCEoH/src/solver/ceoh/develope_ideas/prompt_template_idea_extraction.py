def generate_ideas_prompt(text_content, prompt_iteration, idea_list):
    """
    Generates a prompt for the LLM to provide concrete, actionable ideas for a scoring heuristic
    in a tree search algorithm for the unit load pre-marshalling problem. Emphasizes the importance
    of the provided document and ensures outputs are formatted for easy extraction with curly braces
    and explicit start/end indicators.
    """
    prompt_content = (
        f"The following document may contain crucial information about the unit load pre-marshalling problem:"
        f"\n\n{text_content}\n\n"
        "Carefully analyze the content of this document, as it provides key insights needed to design a scoring heuristic for a tree search algorithm to solve the pre-marshalling problem." 
        "The scoring heuristic will evaluate warehouse states and guide the search process to find solution with the minimal number of moves."
        "'warehouse states' is the size of all potential warehouse states after all potential reshuffling moves."
        "Only the warehouse state with the highest score is selected in a tree search procedure."
        "'warehouse states' is represented by a three levels deep nested list. The second level list represents a warehouse state as a list of lists. The third level list represents a lane of unit loads as a list of integers."
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
        "First example for 'scores': "
            "[0, 1, 3, 1]"
        "Second example for 'scores': "
            "[-3, -1, -4] "
        "\n\n"
        "Using the content of the document, your response should include the following sections, formatted exactly as shown:\n\n"
        "## Challenges Summarized:\n"
        "List the key challenges in designing a scoring heuristic for the pre-marshalling problem. Ensure these are derived from the document.\n\n"
        "## Important Attributes:\n"
        "Identify the most important attributes or metrics discussed in the document that a scoring heuristic should evaluate. "
        "Provide a concise list.\n\n"
        ""
        "## Concrete Heuristic Ideas:\n"
        "Include up to 5 detailed, implementable ideas for scoring heuristics. "
        "The ideas you provide must be rooted in the information and concepts discussed in the document."
        "If you can not find good ideas in the document, dont provide ideas."
        "Use the following format for each idea:\n\n"
        ">>> Start Idea <<<\n"
        "- **Idea Name:** [A name for the idea.]\n"
        "- **Logic:** [A precise explanation of the heuristic's logic and calculation method, directly informed by the document.]\n"
        "- **Challenge Addressed:** [The specific challenge or aspect of the problem it addresses, as outlined in the document.]\n"
        "- **Grounding in the Document** [Explicitly identify the information, metrics, or concepts from the document that this idea is based on. ]\n "
        "- **Implementation:** [Sketch the logic as a python scoring heuristic function named 'select_next_move' that takes 'warehouse_states' as an input and 'scores' as an output. ]\n"
        ">>> End Idea <<<\n\n"
        "Ensure that each idea starts with '>>> Start Idea <<<' and ends with '>>> End Idea <<<'. "
        "This will help ensure proper formatting and enable consistent extraction of ideas."
    )
    if prompt_iteration >= 1:
        prompt_content +=  "These are the ideas returned in a prior request. Do not repeat them. Bring up new ideas or refine them:"
        ideas_content = ""
        for i, indiv in enumerate(idea_list):
            ideas_content += (
                ">>> Start Idea <<<"
                f"- **Idea Name:**: {indiv['Idea Name']}\n"
                f"- **Challenge Addressed:**: {indiv['Logic']}\n"
                f"- **Grounding in the Document:** {indiv['Challenge Addressed']}\n"
                f"- **Implementation:**:"
                f"```python"
                f"{indiv['Implementation']}"
                f"```"
                f">>> End Idea <<<"
            )
        prompt_content += ideas_content
    return prompt_content

def merge_ideas_prompt(idea_list):
    prompt_content = (
        "These are the ideas for a scoring heuristic for the for the pre-marshalling problem."
        "First, go though the ideas identify similar ideas. \n"
        "Second, think abut similar ideas how they relate, and how they can be merged. \n"
        "Third, rework the **Idea, **Logic:**, **Challenge Addressed:**, **Grounding in the Document:**, and **Implementation:** according to the merged idea. \n"
        "Last, add **Merged ideas:** to the response to explain which ideas have been merged, how they relate, and how they been merged. \n"
        
        "Use the following format for each idea:\n\n"
        ">>> Start Idea <<<\n"
        "- **Idea Name:** [A name for the idea.]\n"
        "- **Logic:** [A precise explanation of the heuristic's logic and calculation method, directly informed by the document.]\n"
        "- **Challenge Addressed:** [The specific challenge or aspect of the problem it addresses, as outlined in the document.]\n"
        "- **Grounding in the Document** [Explicitly identify the information, metrics, or concepts from the document that this idea is based on. ]\n "
        "- **Implementation:** [Sketch the logic as a python scoring heuristic function named 'select_next_move' that takes 'warehouse_states' as an input and 'scores' as an output. ]\n"
        "- **Merged Ideas:** [Explain which ideas have been merged, how they relate, and how they been merged. ]\n"
        ">>> End Idea <<<\n\n"
        ""
        "If an idea can not be merged with another return the idea as it is: "
    )

    ideas_content = ""
    for i, indiv in enumerate(idea_list):
        ideas_content += (
            ">>> Start Idea <<<"
            f"- **Idea Name:**: {indiv['Idea Name']}\n"
            f"- **Challenge Addressed:**: {indiv['Logic']}\n"
            f"- **Grounding in the Document:** {indiv['Challenge Addressed']}\n"
            f"- **Implementation:**:"
            f"```python"
            f"{indiv['Implementation']}"
            f"```"
            f">>> End Idea <<<"
        )
    prompt_content += ideas_content

    prompt_content += "\n Do not add any additional information. Do not use any other formatting."

    return prompt_content

def generate_scoring_prompt(all_ideas):
    """
    Generates a prompt for the LLM to evaluate and score the value of each idea for designing
    a scoring heuristic in a tree search algorithm for unit load pre-marshalling.
    """
    prompt = (
        "Below are several ideas for designing a scoring heuristic for a tree search algorithm "
        "to solve the unit load pre-marshalling problem. Your task is to evaluate each idea and assign it a score "
        "from 0.0 to 10.0, where 0.0 means the idea is not valuable and 10.0 means the idea is extremely valuable. "
        "Consider factors like practicality, relevance, and potential impact in designing the heuristic.\n\n"
        "For each idea, return the score in the following JSON-like structure:\n"
        "{\n"
        '  "Idea Name": "Idea name here",\n'
        '  "Score": float_value,\n'
        '  "Reasoning": "Brief reasoning for the score."\n'
        "}\n\n"
        "Here are the ideas:\n"
    )

    for idea in all_ideas:
        prompt += (
            f"{{\n"
            f'  "Idea Name": "{idea["Idea Name"]}",\n'
            f'  "Logic": "{idea["Logic"]}",\n'
            f'  "Challenge Addressed": "{idea["Challenge Addressed"]}",\n'
            f'  "Implementation": "{idea["Implementation"]}"\n'
            f"}}\n\n"
        )

    prompt += (
        "Please provide the evaluation in a structured list of JSON-like entries, one for each idea, following the exact format shown above.\n"
        "Do not include any additional information or formatting in your response to ensure accurate evaluation of the ideas."
    )

    return prompt


