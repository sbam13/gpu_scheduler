from numpy import int32, asarray
from omegaconf import OmegaConf
from os.path import join, dirname
import os, shutil

import jax.random as jr
import numpy as np

from template import SBATCH_TEMPLATE
from math import ceil
from config_structs import Config, DataParams, ModelParams, TrainingParams, Setting, TaskConfig, TaskListConfig

CONFIG_DIR = '../conf/experiment'
SBATCH_DIR = '../sbatch_files'

BASE_DIR = '/tmp/{id}'

CONFIG_NAME = 'sweep_{id}.yaml'
SBATCH_NAME = 'sweep_{id}.bat'

def gen_sweeps(mo_vals, lr_vals, alpha_vals, N_vals, P_vals, ensemble_size: int, ngpus: int,
            bagging_size: int, seed: int, data_seed: int):
    k = jr.PRNGKey(seed)
    lP, la, lN = len(P_vals), len(alpha_vals), len(N_vals)
    seeds = asarray(jr.randint(k, (lP * la * lN,), 0, 10**6
                                ).reshape((lP, la, lN)))

    data_key = jr.PRNGKey(data_seed)
    data_seeds = asarray(jr.randint(data_key, (bagging_size,), 0, 10**6))

    curr_dir = dirname(__file__)
    config_save_folder = join(curr_dir, CONFIG_DIR)
    sbatch_save_folder = join(curr_dir, SBATCH_DIR)

    id = 0
    for mo in mo_vals:
        for lr in lr_vals:
            for bag in range(len(data_seeds)):
                s_D = data_seeds[bag]
                for i in range(len(P_vals)):
                    P = P_vals[i]
                    seed_matrix = seeds[i]
                    config_str = _gen_sweep(id, lr, mo, alpha_vals, N_vals, P, 
                                es=ensemble_size, seed_matrix=seed_matrix, data_seed=s_D)
                    config_fname = CONFIG_NAME.format(id=id)
                    config_rel_loc = join(config_save_folder, config_fname)

                    sbatch_str = SBATCH_TEMPLATE.format(id=id, ngpus=ngpus)

                    sbatch_fname = SBATCH_NAME.format(id=id)
                    sbatch_rel_loc = join(sbatch_save_folder, sbatch_fname)



                    with open(config_rel_loc, mode='x') as fi:
                        fi.write(config_str) # TODO: add file exists exception handler + clean up
                    with open(sbatch_rel_loc, mode='x') as fi:
                        fi.write(sbatch_str) # TODO: add file exists exception handler + clean up
                    id += 1


def _gen_sweep(id, lr, mo, alpha_vals, N_vals, P, es, seed_matrix, data_seed):
    dp = DataParams(P=P, data_seed=int(data_seed))
    tasks = TaskListConfig(data_params=dp)
    STEPS = 24000
    BATCH_SIZE = 256
    num_epochs = ceil(STEPS / (P / BATCH_SIZE))
    for j in range(len(N_vals)):
        N = N_vals[j]
        for i in range(len(alpha_vals)):
            a = alpha_vals[i]
            seed = seed_matrix[i, j]
            tp = TrainingParams(eta_0=lr, epochs=num_epochs, batch_size=BATCH_SIZE, momentum=mo)
            mp = ModelParams(N, a)
            a_N_task = TaskConfig(model_params=mp, training_params=tp, repeat=es, seed=int(seed))
            tasks.task_list.append(a_N_task)
    
    setting = Setting()
    conf = Config(setting, tasks, BASE_DIR.format(id=id))

    str_conf = OmegaConf.to_yaml(conf)
    return '# @package _global_\n' + str_conf


def clear_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

if __name__ == '__main__':
    clear_folder(CONFIG_DIR)
    clear_folder(SBATCH_DIR)
    alphas = list(map(float, np.logspace(-3, 0, 10)))
    P_vals = [2 ** i for i in range(9, 16)]
    # alphas = [1, 10, 100]
    # P_vals = [1024]
    # alphas = [1e0, 1e-1, 1e-2, 1e-3]
    gen_sweeps([.9], [1e-3], alphas, [64], P_vals, 20, 4, 5, 838, 642)