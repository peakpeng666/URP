from copy import deepcopy

import numpy as np
import time

import random

from attr.validators import instance_of

from .eoh_evolution import Evolution
import warnings
from joblib import Parallel, delayed
from .evaluator_accelerate import add_numba_decorator
import re
import concurrent.futures

import os

import json

import multiprocessing
import logging

from datetime import datetime


class InterfaceEC():
    def __init__(self, paras, interface_prob, select, idea_select, **kwargs):

        self.detailed_output = os.environ["DETAILED_OUTPUT"] == 'True'

        print(f'Config timout is ignored: {paras.eva_timeout}')

        # LLM settings
        self.pop_size = paras.ec_pop_size
        self.interface_eval = interface_prob
        prompts = interface_prob.prompts

        self.evol = Evolution(paras, prompts, **kwargs)

        self.m = paras.ec_m
        self.debug = paras.exp_debug_mode

        if not self.debug:
            warnings.filterwarnings("ignore")

        self.select = select

        self.n_p = paras.exp_n_proc

        self.idea_select = idea_select

        self.timeout = paras.eva_timeout
        self.use_numba = paras.eva_numba_decorator

        self.save_file_folder = os.path.join(os.environ["CURRENT_EXPERIMENT"], 'all_programs')

        self.use_idea = paras.ec_use_idea

        self.ideas = None
        if self.use_idea:
            self.idea_number = paras.idea_number
            try:
                print("Loading scored ideas...")
                file_path_ideas = os.path.join(
                    paras.base_path,
                    "data",
                    "eoh_papers_idea_extraction",
                    paras.problem,
                    paras.llm_model_idea,
                    "scored_ideas",
                    "scored_ideas.json"
                )
                with open(file_path_ideas, "r", encoding="utf-8") as f:
                    scored_ideas = json.load(f)
                self.ideas = scored_ideas if self.use_idea else []

            except FileNotFoundError:
                print("ERROR: scored_ideas.json not found.")
                print("Disable Ideas...")
                self.use_idea = False
                raise FileNotFoundError("scored_ideas.json not found. Please check the file path or disable ideas.")


    def check_duplicate(self,population,code):
        for ind in population:
            if code == ind['code']:
                return True
        return False

    def population_generation(self):
        
        n_create = 2
        
        population = []

        for i in range(n_create):
            _,pop = self.get_algorithm([],'i1')
            for p in pop:
                population.append(p)
        return population
    
    def population_generation_seed(self,seeds,n_p):

        population = []
        fitness = []

        if self.n_p > 1:
            fitness, detailed_scores = Parallel(n_jobs=self.n_p)(
                delayed(self.interface_eval.evaluate)(seed['code']) for seed in seeds)

        else:
            for seed in seeds:
                f, _ = self.interface_eval.evaluate(seed['code'])
                fitness.append(f)

        for i in range(len(seeds)):
            try:
                seed_alg = {
                    'algorithm': seeds[i]['algorithm'],
                    'code': seeds[i]['code'],
                    'objective': None,
                    'other_inf': None
                }

                obj = np.array(fitness[i])
                seed_alg['objective'] = float(np.round(obj, 5))
                population.append(seed_alg)

            except Exception as e:
                print("Error in seed algorithm")
                exit()

        print("Initiliazation finished! Get "+str(len(seeds))+" seed algorithms")

        return population
    

    def _get_alg(self,pop,operator):

        offspring = {
            'algorithm': None,
            'code': None,
            'objective': None,
            'other_inf': None
        }

        if self.use_idea:
            ideas = self.idea_select.parent_selection(self.ideas, self.idea_number)
        else:
            ideas = []

        if operator == "i1":
            parents = None
            [offspring['code'],offspring['algorithm']], prompt, full_res =  self.evol.i1()
        elif operator == "e1":
            parents = self.select.parent_selection(pop,self.m)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.e1(parents)
        elif operator == "e2":
            parents = self.select.parent_selection(pop,self.m)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.e2(parents)
        elif operator == "m1":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.m1(parents[0])
        elif operator == "m2":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.m2(parents[0])
        elif operator == "m3":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.m3(parents[0])
        elif operator == "p0":
            parents = self.select.parent_selection(pop,self.m)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.p0(ideas)
        elif operator == "p1":
            parents = self.select.parent_selection(pop, self.m)
            [offspring['code'],offspring['algorithm']], prompt, full_res = self.evol.p1(parents,ideas)
        else:
            print(f"Evolution operator [{operator}] has not been implemented ! \n")

        return parents, offspring, prompt, full_res, ideas

    def get_offspring(self, pop, operator, save_file=""):

        possible_exception = ""
        elapsed_time = None
        detailed_scores = None

        try:

            p, offspring, prompt, full_res, ideas = self._get_alg(pop, operator)

            if offspring is None:
                print("[EOH_EC]: Offspring is none")
                logging.info("[EOH_EC]: Offspring is none")

            if self.use_numba:
                # Regular expression pattern to match function definitions
                pattern = r"def\s+(\w+)\s*\(.*\):"

                # Search for function definitions in the code
                match = re.search(pattern, offspring['code'])

                function_name = match.group(1)

                code = add_numba_decorator(program=offspring['code'], function_name=function_name)
            else :
                code = offspring['code']

            n_retry= 1
            while self.check_duplicate(pop, offspring['code']):
                
                n_retry += 1
                if self.debug:
                    print("[EOH_EC]: duplicated code, wait 1 second and retrying ... ")
                    logging.info("[EOH_EC]: duplicated code, wait 1 second and retrying ... ")

                p, offspring, prompt, full_res, ideas = self._get_alg(pop, operator)

                if self.use_numba:
                    # Regular expression pattern to match function definitions
                    pattern = r"def\s+(\w+)\s*\(.*\):"

                    # Search for function definitions in the code
                    match = re.search(pattern, offspring['code'])

                    function_name = match.group(1)

                    code = add_numba_decorator(program=offspring['code'], function_name=function_name)
                else:
                    code = offspring['code']

                if n_retry > 1:
                    break

            start_time = time.perf_counter_ns()  # Start timing

            if self.n_p > 1:

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.interface_eval.evaluate, code)
                    fitness, detailed_scores = future.result(timeout=self.timeout)
                    offspring['objective'] = float(np.round(fitness, 5))
                    future.cancel()

            else:

                fitness, detailed_scores = self.interface_eval.evaluate(code)
                offspring['objective'] = float(np.round(fitness, 5))


            end_time = time.perf_counter_ns()  # End timing
            elapsed_time = (end_time - start_time)  # Calculate elapsed time

            print(f"Thread Time: {elapsed_time}")
            logging.info(f"Thread Time: {elapsed_time}")


        except Exception as e:

            possible_exception = e
            print(e)
            print("OFFSPRING CREATION FAILED")
            logging.info(f"OFFSPRING CREATION FAILED: {e}")
            offspring = {
                'algorithm': None,
                'code': None,
                'objective': None,
                'other_inf': None,
                'evaluation_time': None
            }
            p = None

        offspring['evaluation_time'] = elapsed_time  # Store the evaluation time
        offspring['offspring_id']= save_file

        offspring_save = deepcopy(offspring)

        add_exception_string = "" if possible_exception == "" else "_Exception"
        with open(os.path.join(self.save_file_folder, f'program_{save_file}{add_exception_string}.json'), 'w+') as file:
            current_file = {
                'exception': str(possible_exception),
                'p': p,
                'offspring': offspring_save,
                'original_code': code,
                'prompt': prompt,
                'full_request': full_res,
                'details': detailed_scores,
                "ideas": ideas
            }

            try:
                current_file['full_request']["response"] = [line + '\n' for line in
                                                            current_file['full_request']["choices"][0]["message"]["content"].split("\n")]
            except:
                pass

            try:
                current_file['full_request']["response"] = [line + '\n' for line in
                                                            current_file['full_request']["response"].split("\n")]
            except:
                pass

            if current_file["offspring"]['algorithm'] is not None:
                current_file["offspring"]['algorithm'] = [line + '\n' for line in current_file["offspring"]['algorithm'].split("\n")]

            if current_file["offspring"]['code'] is not None:
                current_file["offspring"]['code'] = [line + '\n' for line in current_file["offspring"]['code'].split("\n")]

            json.dump(current_file, file, indent=4)

        # Round the objective values
        return p, offspring

    
    def get_algorithm(self, pop, operator, pop_n="0"):
        results = []

        try:
            time_str = datetime.now().strftime("%y%m%d_%H%M%S")
            logging.info(f"Starting parallel execution for population {pop_n} with operator {operator} at {time_str}")

            results = Parallel(n_jobs=self.n_p)(
                delayed(self.get_offspring)(pop, operator, f'pop_{pop_n}_op_{operator}_n{i}_{time_str}') for i in
                range(self.pop_size)
            )

            if self.detailed_output:
                print('###################### Population Results####################')
                print(results)

        except multiprocessing.TimeoutError:
            logging.error("TIMEOUT ERROR IN PARALLEL: This should not be possible!.")
            print("TIMEOUT ERROR IN PARALLEL: This should not be possible!.")
        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            logging.error("Parallel time out.")
            print("Parallel time out.")

        time.sleep(2)

        out_p = []
        out_off = []

        for p, off in results:
            out_p.append(p)
            out_off.append(off)
            if self.debug:
                logging.debug(f">>> check offsprings: \n {off}")
                print(f">>> check offsprings: \n {off}")

        logging.info(f"Finished processing population {pop_n} with operator {operator}.")
        print(f"Finished processing population {pop_n} with operator {operator}.")
        return out_p, out_off