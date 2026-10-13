import os
import re
import json

import sys
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime
from solver.ceoh.develope_ideas.prompt_template_idea_extraction import (generate_ideas_prompt, generate_scoring_prompt,
                                                                merge_ideas_prompt)

def load_text_files(txt_folder):
    """
    Load all text files from the specified folder and return their contents as a dictionary.
    """
    if not os.path.exists(txt_folder):
        raise FileNotFoundError(f"The folder '{txt_folder}' does not exist.")

    text_files = [f for f in os.listdir(txt_folder) if f.endswith(".txt")]
    if not text_files:
        raise FileNotFoundError(f"No text files found in the folder '{txt_folder}'.")

    texts = {}
    for filename in text_files:
        file_path = os.path.join(txt_folder, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            texts[filename] = file.read()

    return texts

def extract_ideas(response, model_name, timestamp, paper_name):
    """
    Extract ideas from the LLM response using regex and explicit start/end markers.
    Assign unique IDs using the format `model_timestamp_count_for_paper`.
    """

    # Normalize line endings to "\n"
    response = re.sub(r"\r\n|\r|\n", "\n", response)

    # Ensure markers like ">>> Start Idea <<<" and ">>> End Idea <<<" are on their own lines
    response = re.sub(r"(>>> Start Idea <<<)", r"\n\1\n", response)
    response = re.sub(r"(>>> End Idea <<<)", r"\n\1\n", response)

    # Remove excessive blank lines (collapse multiple newlines into one)
    response = re.sub(r"\n{2,}", "\n", response)

    # Remove extra spaces around key markers and normalize labels
    response = re.sub(r"(\*\*.*?\*\*):\s+", r"\1: ", response)

    # Strip each line of leading/trailing spaces
    response = "\n".join(line.strip() for line in response.split("\n"))


    pattern = r">>> Start Idea <<<\n(.*?)>>> End Idea <<<"
    matches = re.findall(pattern, response, re.DOTALL)

    if not matches:
        print("No matches found with the pattern.")

    ideas = []
    for count, match in enumerate(matches, start=1):
        unique_id = f"{model_name}_{timestamp}_{count}_for_{paper_name}"

        name_match = re.search(r"- \*\*Idea Name:\*\* (.*?)\n", match)
        logic_match = re.search(r"- \*\*Logic:\*\* (.*?)\n", match, re.DOTALL)
        challenge_match = re.search(r"- \*\*Challenge Addressed:\*\* (.*?)\n", match, re.DOTALL)
        grounding_match = re.search(r"- \*\*Grounding in the Document:\*\* (.*?)\n", match, re.DOTALL)
        implementation_match = re.search(r"- \*\*Implementation:\*\*([\s\S]*?)(?=(?:\n- \*\*|$))", match, re.DOTALL)
        merged_ideas_match = re.search(r"- \*\*Merged Ideas:\*\* (.*?)(?:\n|$)", match, re.DOTALL)

        ideas.append({
            "id": unique_id,
            "count": count,
            "paper_pdf_name": paper_name,
            "timestamp": timestamp,
            "llm_model": model_name,
            "Idea Name": name_match.group(1) if name_match else None,
            "Logic": logic_match.group(1) if logic_match else None,
            "Challenge Addressed": challenge_match.group(1) if challenge_match else None,
            "Grounding in the Document": grounding_match.group(1) if grounding_match else None,
            "Implementation": implementation_match.group(1) if implementation_match else None,
            "Merged Ideas": merged_ideas_match.group(1) if merged_ideas_match else None,
        })

    return ideas

def sanitize_folder_name(folder_name):
    """
    Replace invalid characters in folder names with underscores.
    """
    return re.sub(r'[<>:"/\\|?*]', ' ', folder_name)

def save_prompt_and_response_to_file(prompt, response, llm_name, timestamp, save_folder):
    """
    Save the given prompt and response to a JSON file.
    Each file is saved in a subfolder named after the LLM used, with invalid characters replaced.
    """

    # Create the JSON data structure
    log_entry = {
        "timestamp": timestamp,
        "llm_name": llm_name,
        "prompt": prompt,
        "response": response
    }

    # Write the JSON data to the file
    with open(save_folder, "w", encoding="utf-8") as file:
        json.dump(log_entry, file, indent=4, ensure_ascii=False)

    print(f"Prompt and response saved to: {save_folder}")

def save_ideas_to_file(ideas, ideas_folder):
    """
    Save the extracted ideas to a JSON file in a subfolder named after the sanitized LLM name.
    """

    # Save ideas to the file
    with open(ideas_folder, "w", encoding="utf-8") as file:
        json.dump(ideas, file, indent=4, ensure_ascii=False)

    print(f"Ideas saved to: {ideas_folder}")

def extract_ideas_from_files(txt_folder, ideas_folder, prompt_response_folder, llm, model_name, prompt_iterations= 1, skip_extracted=False):
    """
    Extract ideas from text files and save them as JSON files, organized in LLM-specific subfolders.
    """
    try:
        texts = load_text_files(txt_folder)
    except FileNotFoundError as e:
        print(e)
        return

    for filename, text_content in texts.items():
        print(f"\nAnalyzing '{filename}'...")
        paper_name = os.path.splitext(filename)[0]



        idea_list = []
        for i in range(0,prompt_iterations+1):

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create a subfolder for the specific LLM name
            if not os.path.exists(ideas_folder):
                os.makedirs(ideas_folder)

            if not os.path.exists(prompt_response_folder):
                os.makedirs(prompt_response_folder)

            save_prompt_response_path = os.path.join(prompt_response_folder, f"{paper_name}_prompt_response_{i}.json")
            save_ideas_path = os.path.join(ideas_folder, f"{paper_name}_iter_{i}.json")

            if os.path.exists(save_ideas_path) and skip_extracted:
                if i < prompt_iterations:
                    print(f"Skipping iteration {i + 1}/{prompt_iterations} as ideas already extracted. in {save_ideas_path}")
                else:
                    print(f"Skipping summarizing ideas as already extracted. in {save_ideas_path}")
                continue

            if i < prompt_iterations:
                print(f"\nIteration {i + 1}/{prompt_iterations} ")
                # Generate ideas if not already extracted
                ideas_prompt = generate_ideas_prompt(text_content, i, idea_list)
                response, _ = llm.get_response(ideas_prompt)
            else:
                if prompt_iterations != 1:
                    print(f"\nSummarize ideas")
                    ideas_prompt = merge_ideas_prompt(idea_list)
                    response, _ = llm.get_response(ideas_prompt)
                else:
                    continue

            # Save each prompt and response to a separate JSON file
            save_prompt_and_response_to_file(ideas_prompt, response, model_name, timestamp, save_prompt_response_path)

            if response:
                extracted_ideas = extract_ideas(response, model_name, timestamp, paper_name)
                idea_list.extend(extracted_ideas)
                save_ideas_to_file(extracted_ideas, save_ideas_path)
            else:
                print(f"Failed to get a response from the LLM for '{filename}'.")

def load_ideas(ideas_folder, prompt_iterations):
    """
    Load all JSON files containing ideas from the specified folder and return a list of all ideas.
    """
    if not os.path.exists(ideas_folder):
        raise FileNotFoundError(f"The folder '{ideas_folder}' does not exist.")

    idea_files = [f for f in os.listdir(ideas_folder) if f.endswith(f"{prompt_iterations}.json")]
    if not idea_files:
        raise FileNotFoundError(f"No idea files found in the folder '{ideas_folder}'.")

    all_ideas = []
    for file_name in idea_files:
        file_path = os.path.join(ideas_folder, file_name)
        with open(file_path, "r", encoding="utf-8") as file:
            ideas = json.load(file)
            all_ideas.extend(ideas)

    for i, idea in enumerate(all_ideas, start=1):
        idea["count"] = i

    return all_ideas

def score_ideas(all_ideas, llm):
    """
    Generate a scoring prompt, retrieve scores for the ideas using the LLM, and assign the scores to the ideas.
    """
    scoring_prompt = generate_scoring_prompt(all_ideas)
    print("Scoring prompt:\n",scoring_prompt)
    scoring_response, _ = llm.get_response(scoring_prompt)

    if scoring_response:
        print(f"Raw response from LLM for scoring ideas:\n{scoring_response}\n")

        # Parse scores from the response
        scored_ideas = parse_scores_from_response(scoring_response)

        if scored_ideas:
            print("Parsed scored ideas:", scored_ideas)  # Debugging output

            # Match parsed scores to their corresponding ideas
            for idea, scored in zip(all_ideas, scored_ideas):
                idea["Score"] = scored.get("Score", 0)
                idea["Reasoning"] = scored.get("Reasoning", "No reasoning provided.")

            # Sort ideas by score in descending order
            return sorted(all_ideas, key=lambda x: x["Score"], reverse=True)
        else:
            print("Failed to parse scores from LLM response.")
    else:
        print("Failed to get a response from the LLM for idea scoring.")

    # Return the original ideas with a default score of 0
    for idea in all_ideas:
        idea["Score"] = 0
        idea["Reasoning"] = "No score available."
    return all_ideas

def parse_scores_from_response(response):
    """
    Parse scores from the LLM response.
    Handles malformed JSON-like responses and converts them into a proper JSON array.
    """
    try:
        # Strip unexpected headers or trailing parts like `json`
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove `json` and leading backticks
        if response.endswith("```"):
            response = response[:-3]  # Remove trailing backticks

        # Replace `}{` with `}, {` to separate JSON objects
        response = re.sub(r"}\s*{", "},\n{", response.strip())

        # Attempt to parse directly as JSON
        try:
            scored_ideas = json.loads(response)
            # If it's already a list of dictionaries, return it directly
            if isinstance(scored_ideas, list) and all(isinstance(item, dict) for item in scored_ideas):
                return scored_ideas
        except json.JSONDecodeError:
            pass

        # Wrap response in square brackets to form a valid JSON array
        response = f"[{response}]"

        # Attempt to parse as JSON again
        scored_ideas = json.loads(response)

        # If it's a nested list, flatten it
        if isinstance(scored_ideas, list) and len(scored_ideas) == 1 and isinstance(scored_ideas[0], list):
            return scored_ideas[0]

        return scored_ideas
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON-like response: {e}")
        return []

def save_scored_ideas(scored_ideas, output_file):
    """
    Save the scored ideas to a JSON file. Creates the folder if it doesn't exist.
    """
    # Get the directory name from the output file path
    folder = os.path.dirname(output_file)

    # Check if the folder exists, and create it if it doesn't
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created folder: {folder}")

    # Write the scored ideas to the JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(scored_ideas, file, indent=4, ensure_ascii=False)
    print(f"Scored ideas saved to: {output_file}")

