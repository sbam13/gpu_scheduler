from itertools import product
from numpy import int32, asarray
from omegaconf import OmegaConf
from os.path import join, dirname

import jax.random as jr

from template import SBATCH_TEMPLATE

from config_structs import Config, DataParams, ModelParams, TrainingParams, Setting, TaskConfig, TaskListConfig

CONFIG_DIR = '../conf/experiment'
SBATCH_DIR = '../sbatch_files'

BASE_DIR = '/tmp/{id}'

CONFIG_NAME = 'sweep_{id}.yaml'
SBATCH_NAME = 'sweep_{id}.bat'

def gen_sweeps(lr_vals, alpha_vals, N_vals, P_vals, ensemble_size: int, ngpus: int,
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
    for lr in lr_vals:
        for bag in range(len(data_seeds)):
            s_D = data_seeds[bag]
            for i in range(len(P_vals)):
                P = P_vals[i]
                seed_matrix = seeds[i]
                config_str = _gen_sweep(id, lr, alpha_vals, N_vals, P, 
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


def _gen_sweep(id, lr, alpha_vals, N_vals, P, es, seed_matrix, data_seed):
    dp = DataParams(P=P, data_seed=int(data_seed))
    tasks = TaskListConfig(data_params=dp)
    
    for j in range(len(N_vals)):
        N = N_vals[j]
        for i in range(len(alpha_vals)):
            a = alpha_vals[i]
            seed = seed_matrix[i, j]
            tp = TrainingParams(eta_0=lr, epochs=160)
            mp = ModelParams(N, a)
            a_N_task = TaskConfig(model_params=mp, training_params=tp, repeat=es, seed=int(seed))
            tasks.task_list.append(a_N_task)
    
    setting = Setting()
    conf = Config(setting, tasks, BASE_DIR.format(id=id))

    str_conf = OmegaConf.to_yaml(conf)
    return '# @package _global_\n' + str_conf


if __name__ == '__main__':
    gen_sweeps([10 ** -c for c in range(2, 5)], [1e-2, 1e-3, 1e-4], [64], [16384], 1, 1, 1, 4256, 29384)