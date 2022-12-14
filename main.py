#!/usr/bin/env python3
import logging
import time

from omegaconf import DictConfig

import hydra

from os.path import join

from src.run.save_helpers import copy_results_into_permanent

from src.experiment.names import names
from src.run.run_tasks import run_tasks
from src.run import constants

import jax

# TODO: timing!

log = logging.getLogger(__name__)

@hydra.main(version_base=None, config_path='conf', config_name='config')
def main(cfg: DictConfig):
    log.info(f'Found {len(jax.devices())} device(s).')
    # cfg = (setting, hyperparams)
    setting = cfg.setting
    try:
        ds_name, model_name = setting['dataset'], setting['model']
        module_ = names[ds_name, model_name]
    except KeyError:
        raise ValueError('Invalid experimental setting.')

    hp_list = cfg.hyperparams.task_list
    
    reader = module_.TaskReader(hp_list)
    
    base_dir = cfg.base_dir
    
    PD = module_.PreprocessDevice(base_dir, cfg.hyperparams.data_params)
    
    log.info('Loading data...')
    PD.preprocess()
    log.info('...done.')

    log.info('Running tasks...')
    run_tasks(reader.tasks, PD)
    log.info('...all tasks complete.')

    log.info('Moving results into permanent...')
    timestr = time.strftime("%Y%m%d-%H%M%S")
    permanent_results_dirname = 'results-' + timestr
    copy_results_into_permanent(PD.save_dir, permanent_results_dirname)
    log.info('...done.')


if __name__ == '__main__':
    main()


    



