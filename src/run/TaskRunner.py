import logging
from jax.random import split
from jax import device_get
from src.experiment.training.momentum import Result
from src.run.PreprocessDevice import PreprocessDevice

from src.tasks.task import Task, Task_ConfigSubset

from os.path import join, exists
from os import mkdir

from omegaconf import OmegaConf

from pickle import dump

class TaskRunner:
    def __init__(self, PD: PreprocessDevice) -> None:
        self.preprocess_device = PD

    def run_serial_task(self, task: Task):
        key = task.seed
        keys = split(key, num=task.repeat).reshape((task.repeat, 2))
        data = self.preprocess_device.data

        save_folder = join(self.preprocess_device.save_dir, f'task-{task._id}')
        for r in range(task.repeat):            
            result = task.apply_callback(keys[r], data)
            
            repeat_save_folder = join(save_folder, f'trial-{r}')
            task.save_callback(repeat_save_folder, result)

    def run_repeat_task(self, task: Task):
        iters = task.repeat // num_devices
        # TODO: num_devices doesn't actually have to divide task.repeat!
        key = task.seed
        iter_keys = split(key, num=iters)
        del key

        apply = task.apply_callback

        save_folder = join(self.preprocess_device.save_dir, f'task-{task._id}')
        if exists(save_folder):
            raise RuntimeError(f'Save folder for task {task._id} already exists.')
        else:
            mkdir(save_folder)
            save_config(save_folder, task)
            

        # TODO: this is hacky. separate into grid-search hyperparams
        # recall `apply` is (RNG, data, model_params, training_params) -> result
        # papply = pmap(apply, static_broadcasted_argnums=(2, 3)) # apply (key, data) -> result

        data = self.preprocess_device.data
        devices = self.preprocess_device.devices
        num_devices = len(devices)
        
        mp, tp = dict(task.model_params), dict(task.training_params)
        
        
        for batch in range(0, iters):
            key = iter_keys[batch]
            batch_results = apply(key, data, devices, mp, tp)

            idx = batch * num_devices
            for replica, result in enumerate(batch_results):
                local_result = device_get(result)
                repeat_save_folder = join(save_folder, f'trial-replica-{idx + replica}')
                if exists(repeat_save_folder):
                    raise RuntimeError(f'Save folder for replica {idx + replica} for task {task._id} already exists.')
                else:
                    mkdir(repeat_save_folder)
                    save_result(repeat_save_folder, local_result)
                del local_result
            
            del local_result, result

def save_config(dir: str, task: Task):
    fname = 'task_config.yaml'
    abs_path_fname = join(dir, fname)
    tcs = Task_ConfigSubset(task.model, task.dataset, task.model_params, task.training_params)
    tcs_yaml = OmegaConf.to_yaml(tcs)
    try:
        with open(abs_path_fname, 'x') as f:
            f.write(tcs_yaml)
    except OSError:
        logging.error('Could not write task config file.')
        raise

def save_result(dir: str, result: Result):
    fname = 'trial_result.pkl'
    abs_path_fname = join(dir, fname)
    try:
        with open(abs_path_fname, 'xb') as f:
            dump(result, f)
    except OSError:
        logging.error(f'Could not write task result file in directory "{dir}".')
        raise
