import time
import numpy as np
import sys
import types
import warnings
import datetime
import os
import threading
from multiprocessing import Process, Queue

from solver.ceoh.problems.descriptions.upmp.multibay_reshuffeling.prompts import GetPrompts

from util.mr_to_ceoh_util import (
    load_experiments,
    get_access_directions,
    create_virtual_lane,
    get_virtual_lane_score,
    convert_vl_to_list,
    create_lanes)

from problems.multibay_reshuffeling.bay.warehouse import Warehouse

MAX_NUMBER_OF_MOVES = 100
TIMEOUT_SECONDS = 60
USE_REFERENCE_SOLUTION = True
N_WORKERS = 10


def mutlibay_reshuffeling(priority, wh: Warehouse, paras=None):
    start = datetime.datetime.now()
    current_move_number = 0

    while (get_virtual_lane_score(convert_vl_to_list(wh.virtual_lanes)) > 0
           and start.second + TIMEOUT_SECONDS > datetime.datetime.now().second
           and current_move_number < MAX_NUMBER_OF_MOVES):

        possible_lanes, moves = create_lanes(wh)
        virtual_lane_as_list = [convert_vl_to_list(inst) for inst in possible_lanes]

        if paras is None:
            fs_prio = priority.select_next_move(virtual_lane_as_list)
        else:
            fs_prio = priority.select_next_move(virtual_lane_as_list, paras)

        selection_index = np.argmax(fs_prio)
        wh.virtual_lanes = possible_lanes[selection_index]
        current_move_number += 1

    return current_move_number


def reshuffle_worker_main(task_queue, result_queue, code_string, base_path):
    while True:
        job = task_queue.get()
        if job is None:
                break

        index, config = job
        try:
            heuristic_module = types.ModuleType("heuristic_module")
            exec(code_string, heuristic_module.__dict__)

            access_directions = get_access_directions(config)
            layout_file = config['layout_file'].split("/")[-1]
            layout_file_path = os.path.join(base_path, layout_file)

            wh = Warehouse(layout_file_path, access_directions)
            wh.virtual_lanes = create_virtual_lane(config)

            eval_start_time = time.perf_counter()
            score = mutlibay_reshuffeling(heuristic_module, wh)
            eval_time = time.perf_counter() - eval_start_time

            ref_score = config['h_initial']
            if score == 0 and ref_score != 0:
                fitness = 1
            elif score == 0:
                fitness = 0
            else:
                fitness = (score - ref_score) / ref_score

            result_queue.put((index, {
                'fitness': fitness,
                'moves': score,
                'reference': ref_score,
                'eval_time': eval_time
            }))
        except Exception as e:
            result_queue.put((index, {
                'fitness': None,
                'error': str(e)
            }))


class MULTIBAY_RESHUFFLECONST:
    def __init__(self, eoh_experiment_file, code_string=None, paras=None):
        global MAX_NUMBER_OF_MOVES, TIMEOUT_SECONDS
        if paras is not None:
            MAX_NUMBER_OF_MOVES = paras.get('MAX_NUMBER_OF_MOVES', MAX_NUMBER_OF_MOVES)
            TIMEOUT_SECONDS = paras.get('TIMEOUT_SECONDS', TIMEOUT_SECONDS)
            print(TIMEOUT_SECONDS)
            print(paras)




        self.prompts = GetPrompts()
        self.instance_configs, self.ref_scores = load_experiments(eoh_experiment_file)

        if len(self.instance_configs) == 0:
            print("[INSTANCES ERROR]: No Instances available")
            exit(1)

        if code_string is not None:
            self.fitness = self.evaluate(code_string, paras)

    def evaluate(self, code_string, paras=None):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                instance_configs = self.instance_configs
                number_of_exp = len(instance_configs)

                base_path = os.path.join(os.getenv('BASE_PATH'), 'data', 'mr_examples')

                managers = []
                for _ in range(N_WORKERS):
                    task_queue = Queue()
                    result_queue = Queue()
                    p = Process(target=reshuffle_worker_main, args=(task_queue, result_queue, code_string, base_path))
                    p.start()
                    managers.append((p, task_queue, result_queue))

                results = [None] * number_of_exp
                buckets = [[] for _ in range(N_WORKERS)]

                for i, config in enumerate(instance_configs):
                    buckets[i % N_WORKERS].append((i, config))

                threads = []

                def run_manager(index, jobs):
                    process, task_queue, result_queue = managers[index]
                    for i, config in jobs:
                        task_queue.put((i, config))

                        start_time = time.time()
                        result = None

                        while (time.time() - start_time) < TIMEOUT_SECONDS:
                            try:
                                candidate = result_queue.get(timeout=0.1)
                                if candidate is not None:
                                    result = candidate
                                    break
                            except:
                                pass

                        if result is not None:
                            results[i] = result
                        else:
                            # forcefully terminate the process handling this job
                            process.terminate()
                            results[i] = {
                                'fitness': None,
                                "moves" : None,
                                'reference': config['h_initial'],
                                'eval_time': TIMEOUT_SECONDS,
                                'error': f"Timeout after {TIMEOUT_SECONDS}s"
                            }

                    task_queue.put(None)
                    # Restart worker for next job if needed
                    process.join()

                for i in range(N_WORKERS):
                    t = threading.Thread(target=run_manager, args=(i, buckets[i]))
                    t.start()
                    threads.append(t)

                for t in threads:
                    t.join()

                detailed_fitness = []
                h_initials = []
                algo_moves = []
                eval_times = []
                overall_score = 0

                print(results)

                for result in results:
                    r = result[1] if isinstance(result, tuple) else result
                    if r.get("fitness") is None:
                        print("[ERROR] Worker error:", r.get("error"))
                    detailed_fitness.append(r['fitness'])
                    algo_moves.append(r['moves'])
                    h_initials.append(r['reference'])
                    eval_times.append(r['eval_time'])
                    overall_score += r['fitness']

                details = {
                    'detailed_fitness': detailed_fitness,
                    'moves': algo_moves,
                    'reference': h_initials,
                    'eval_time': eval_times
                }

                print(f'Overall fitness: {overall_score / number_of_exp}', flush=True)
                return (overall_score / number_of_exp), details

        except Warning as w:
            print(f"[ERROR] A warning was raised and treated as an error: {w}")
            return None
        except Exception as e:
            print(f"[ERROR] An exception occurred: {e}")
            return None


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()

    code_string = """
def select_next_move(warehouse_states):
    scores = []
    for state in warehouse_states:
        score = 0
        total_lanes = len(state)

        for lane in state:
            block_count = 0
            seen_prio = float('inf')
            distance_penalty_factor = len(lane)
            accessible_priority_sum = 0

            for unit in reversed(lane):
                if unit != 0 and unit > seen_prio:
                    block_count += 1
                    penalty = (6 - unit) * distance_penalty_factor
                    score -= penalty

                if unit != 0:
                    seen_prio = min(seen_prio, unit)
                    accessible_priority_sum += unit
                    distance_penalty_factor -= 1

            if block_count == 0:
                reward = sum(unit for unit in lane if unit != 0) ** 2.5 / len(lane)
                score += reward + accessible_priority_sum

        # Calculate deviation from sorted order and apply penalty
        total_deviation = 0
        for lane in state:
            ideal_lane = [x for x in lane if x != 0] + [0] * lane.count(0)
            actual_lane = lane[:]
            while ideal_lane != actual_lane:
                for i in range(len(actual_lane) - 1):
                    if actual_lane[i] > actual_lane[i + 1]:
                        actual_lane[i], actual_lane[i + 1] = actual_lane[i + 1], actual_lane[i]
                        total_deviation += 1

        score -= total_deviation * 0.5

        scores.append(score)

    return scores

"""
    start_time = time.time()
    eoh_experiment_file = "exp_bay5_wh_1_fill_0.6.json"
    reshuffle_const = MULTIBAY_RESHUFFLECONST(eoh_experiment_file, code_string)
    end_time = time.time()

    if reshuffle_const.fitness is not None:
        print("Fitness Score:", reshuffle_const.fitness)
    else:
        print("Evaluation failed due to an error in the provided heuristic code.")

    print("Total Execution Time:", end_time - start_time, "seconds")
