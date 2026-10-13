import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import click

from solver.ceoh.utils.getParas import Paras
from solver.ceoh.llm.models import get_model_info
from solver.ceoh.llm.interface_LLM import InterfaceLLM
from solver.ceoh.develope_ideas.covert_pdf_to_txt import convert_pdfs_to_text
from solver.ceoh.develope_ideas.analyze_txt_with_llm import (
    sanitize_folder_name, extract_ideas_from_files, load_ideas,
    score_ideas, save_scored_ideas
)

@click.group()
@click.pass_context
def main(ctx):
    pass

@main.command()
@click.option('--model_name', default="llama3.1:70b", help='LLM model')
@click.option('--problem', default="multibay_reshuffeling", help='Problem for generating ideas')
@click.option('--prompt_iterations', default=5, help='Problem for generating ideas')
@click.option('--skip_extracted', default=True, help='Problem for generating ideas')
@click.option('--skip_rating', default=True, help='Problem for generating ideas')
def run(
        model_name: str,
        problem: str,
        prompt_iterations: int,
        skip_extracted: bool,
        skip_rating: bool):


    llm_api_endpoint, add_url_info, api_key, llm_use_local = \
         get_model_info(model_name)

    debug_mode = os.getenv("DEBUG_MODE", True)
    llm_temperature = os.getenv("LLM_TEMPERATURE", None)

    paras = Paras()

    paras.set_paras(
        llm_api_endpoint=  llm_api_endpoint,
        llm_api_key= api_key,
        llm_model= model_name,
        exp_debug_mode= debug_mode,
        llm_use_local= llm_use_local,
        llm_local_url= llm_api_endpoint,
        llm_temperature= llm_temperature,
        llm_url_info= add_url_info,
     )

    # Print parameters for debugging
    print("LLM Parameters:", paras)

    # Initialize LLM Interface with the dictionary
    llm = InterfaceLLM(paras)

    data_path = os.path.join(os.getenv("BASE_PATH"), "data")

    # Paths to folders
    pdf_folder = os.path.join(data_path, "eoh_papers_pdf")
    txt_folder = os.path.join(data_path, "eoh_papers_txt")

    ideas_folder = os.path.join(data_path, "eoh_papers_idea_extraction", problem, sanitize_folder_name(model_name),  "ideas")
    prompt_response_folder = os.path.join(data_path, "eoh_papers_idea_extraction", problem, sanitize_folder_name(model_name), "prompt_response")

    output_file = os.path.join(data_path, "eoh_papers_idea_extraction", problem, sanitize_folder_name(model_name), "scored_ideas", f"scored_ideas.json")

    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)
    if not os.path.exists(ideas_folder):
        os.makedirs(ideas_folder)
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
        print(f"Please add pdfs to the folder: {pdf_folder}")
        exit(1)

    convert_pdfs_to_text(pdf_folder, txt_folder)

    extract_ideas_from_files(txt_folder, ideas_folder,prompt_response_folder, llm, model_name, prompt_iterations, skip_extracted)

    try:
        all_ideas = load_ideas(ideas_folder, 0)
    except FileNotFoundError as e:
        print(e)
        return

    if  skip_rating:
        print("Skipping idea scoring.")
        scored_ideas = all_ideas
    else:
        scored_ideas = score_ideas(all_ideas, llm)

    save_scored_ideas(scored_ideas, output_file)

