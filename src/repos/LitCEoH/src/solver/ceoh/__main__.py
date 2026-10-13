import os
import click
import logging

import solver.ceoh.eoh as eoh
from solver.ceoh.utils.getParas import Paras
from solver.ceoh.llm.models import get_model_info
from solver.ceoh.utils.createFolders import check_instances, create_idea_folders, save_paras


@click.group()
@click.pass_context
def main(ctx):
    pass

@main.command()
@click.argument("problem")
@click.option('--model_name', default="llama3.1:70b", help='LLM model')
@click.option('--use_example', default=1, help='Use Example for LMM request')
@click.option('--ideas_iteration_start', default=-1, help='Use Idea start for LMM request. If -1 its disabled')
@click.option('--continue_target_folder', default="None", help='Folder for continue experiemnts')
@click.option('--continue_target_pop', default=1, help='Population to continue.')
@click.option('--injection_loops', default=-1, help='Number of extraction loops.')
@click.option('--ec_operators', default="e1,e2,m1,m2", help='Prompt strategies')
@click.option('--ec_n_pop', default="20", help='Number of populations')
@click.option('--ec_m', default="5", help='Number of parents in prompts.')
@click.option('--ec_pop_size', default="20", help='Number of times each active strategy is called.')
@click.option('--exp_n_proc', default="1", help='Number of parallel processes.')
@click.option('--ui_experiment', default="None", help='Experiment variation indicator.')
@click.option('--eoh_experiment_file', default="exp_1.json", help='File with experiment config.')
@click.option('--use_math_model', default=0, help='Use math model for LMM request')
@click.option('--idea_number', default=-1, help='Number of ideas use in P1. If -1 its disabled')
def run(problem, model_name, use_example,
         ideas_iteration_start, continue_target_folder, continue_target_pop, injection_loops,
        ec_operators, ec_n_pop, ec_m , ec_pop_size, ui_experiment, exp_n_proc, eoh_experiment_file, use_math_model, idea_number):


    if continue_target_folder == "None":
        exp_continue_pop_nr = 20
        exp_continue_folder = "experiment"
        set_init_pop = False
    else:
        exp_continue_pop_nr = continue_target_pop
        exp_continue_folder = continue_target_folder
        set_init_pop = True

    # Parameter initialization
    paras = Paras()

    llm_api_endpoint, add_url_info, api_key, llm_use_local = \
         get_model_info(model_name)

    paras.set_paras(
        eoh_experiment_file = eoh_experiment_file,
        llm_api_key=api_key,
        llm_api_endpoint=llm_api_endpoint,
        llm_use_local=llm_use_local,
        llm_url_info=add_url_info,
        method="eoh",  # ['eoh']
        problem=problem,
        llm_model=model_name,
        llm_local_url=llm_api_endpoint,
        ec_pop_size=int(ec_pop_size),  # number of samples in each population
        ec_operators=ec_operators.split(','),  # operators in EoH
        ec_use_example=bool(use_example),
        ec_use_idea= ideas_iteration_start > 0 or "p" in ec_operators,
        ec_n_pop=int(ec_n_pop),  # number of populations
        exp_n_proc=int(exp_n_proc),  # number of parallel processes
        ec_m = int(ec_m),  # number of parents for 'e1' and 'e2' operators, default = 2
        exp_debug_mode=False,
        eva_numba_decorator=False,
        exp_continue_pop_nr = int(exp_continue_pop_nr),
        exp_continue_folder = exp_continue_folder,
        exp_use_continue = int(set_init_pop),
        llm_temperature=None,
        injection_loops=int(injection_loops),
        ideas_iteration_start=int(ideas_iteration_start),
        idea_number = int(idea_number),
        idea_type = ui_experiment,
        ec_use_math_model = bool(use_math_model),
    )

    # initilization
    evolution = eoh.EVOL(paras)

    current_folder = os.environ["CURRENT_EXPERIMENT"]

    # let logging
    logging.basicConfig(
        level=logging.DEBUG,  # Set the logging level to DEBUG or INFO as needed
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=os.path.join(current_folder, 'parallel_log.log'),  # Specify a log file
        filemode='w'  # Use 'w' to overwrite the log file each time, or 'a' to append
    )

    save_paras(paras)

    create_idea_folders(paras)

    check_instances(paras)

    # run
    evolution.run()
