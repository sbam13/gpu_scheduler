from omegaconf import OmegaConf

from src.run.constants import REMOTE_RESULTS_FOLDER
from src.experiment.training.Result import Result

from collections import defaultdict

import os
import numpy as np
from os.path import join

import pickle

from tqdm import tqdm

def read_result(fname):
    with open(fname, 'rb') as f:
        res = pickle.load(f)
    return res


def see_lr_losses(FOLDER=REMOTE_RESULTS_FOLDER):
    results_files = os.listdir(FOLDER)
    for rf in results_files:
        if not rf.startswith('results-20221101'):
            continue
        for task in range(1):
            task_folder = join(FOLDER, rf, f'task-{task}')
            try:
                conf = OmegaConf.load(join(task_folder, 'task_config.pkl'))
            except:
                conf = OmegaConf.load(join(task_folder, 'task_config.yaml'))
            with open(join(task_folder, 'trial_0_result.pkl'), 'rb') as f:
                res = pickle.load(f)
            lr = conf.training_params.eta_0
            alpha = conf.model_params.alpha
            print('rf', rf, 'LR: ', lr, ' alpha: ', alpha)
            print('Train Losses: ', res.train_losses[-5:], '\n')

def see_lr_deviations(FOLDER=REMOTE_RESULTS_FOLDER):
    results_files = os.listdir(FOLDER)
    total_res = []
    for rf in tqdm(results_files):
        res = {}
        rf_loc = join(FOLDER, rf)
        data_conf = OmegaConf.load(join(rf_loc, 'data_config.yaml'))
        res['data_config'] = data_conf
        num_tasks = len(os.listdir(rf_loc)) - 1
        for task in range(num_tasks):
            task_str = f'task-{task}'
            task_folder = join(rf_loc, task_str)
            task_conf = OmegaConf.load(join(task_folder, 'task_config.yaml'))
            num_trials = len(os.listdir(task_folder)) - 1
            trial_results = []
            for trial in range(num_trials):
                with open(join(task_folder, f'trial_{trial}_result.pkl'), 'rb') as f:
                    trial_results.append(pickle.load(f))
            res[task_str] = (task_conf, trial_results)
        total_res.append(res)
    return total_res


def overall_losses(trials):
    return [trial.test_loss_f for trial in trials]

def average_and_ensemble_loss(trials):
    def mse(y, yhat):
        return np.mean((y - yhat)**2)
    
    if len(trials) == 0:
        raise ValueError

    num_trials = len(trials)
    y_true = trials[0].test_y
    
    nan_indices = {i for i in range(len(trials)) if np.isnan(trials[i].test_loss_f)}
    
    ensemble_preds = np.zeros_like(trials[0].test_yhat_f)
    j = 0
    for i in range(len(trials)):
        if i in nan_indices:
            continue
        ensemble_preds += trials[i].test_yhat_f
        j += 1
    if j != 0:
        ensemble_preds /= j

    assert ensemble_preds.shape == y_true.shape
    
    trial_losses = [trials[i].test_loss_f for i in range(num_trials) if i not in nan_indices]
    return np.mean(trial_losses), mse(ensemble_preds, y_true), len(nan_indices)

def average_and_ensemble_accuracy(trials):
    def accuracy(y, yhat):
        return np.sum(y * yhat > 0) / y.size
    
    if len(trials) == 0:
        raise ValueError

    num_trials = len(trials)
    y_true = trials[0].test_y
    
    nan_indices = {i for i in range(len(trials)) if np.isnan(trials[i].test_loss_f)}
    
    trial_accuracies = []
    ensemble_preds = np.zeros_like(trials[0].test_yhat_f)
    j = 0
    for i in range(len(trials)):
        if i in nan_indices:
            continue
        trial_yhat = trials[i].test_yhat_f
        trial_accuracies.append(accuracy(trial_yhat, y_true))
        ensemble_preds += trial_yhat
        j += 1
    if j != 0:
        ensemble_preds /= j

    assert ensemble_preds.shape == y_true.shape
    
    return np.mean(trial_accuracies), accuracy(ensemble_preds, y_true), len(nan_indices)


def average_f_train_loss(trials):
    if len(trials) == 0:
        raise ValueError

    num_trials = len(trials)
    
    nan_indices = {i for i in range(len(trials)) if np.isnan(trials[i].test_loss_f)}
    
    trial_losses = [trials[i].train_losses[-1] for i in range(num_trials) if i not in nan_indices]
    return np.mean(trial_losses), len(nan_indices)

def get_overall_losses(results_list):
    nested = defaultdict(lambda: defaultdict(dict))
    for res in results_list:
        data_seed = res['data_config']['data_seed']
        P = res['data_config']['P']
        num_tasks = len(res) - 1
        for i in range(num_tasks):
            task = res[f'task-{i}']
            task_config = task[0]
            alpha = task_config['model_params']['alpha']
            ol = overall_losses(task[1])
            nested[data_seed][P][alpha] = ol
    return nested

def get_losses(results_list, P_first=True):
    nested_al = defaultdict(lambda: defaultdict(dict))
    nested_el = defaultdict(lambda: defaultdict(dict))
    nested_num_nan = defaultdict(lambda: defaultdict(dict))
    for res in results_list:
        data_seed = res['data_config']['data_seed']
        P = res['data_config']['P']
        num_tasks = len(res) - 1
        for i in range(num_tasks):
            task = res[f'task-{i}']
            task_config = task[0]
            alpha = task_config['model_params']['alpha']
            al, el, num_nan = average_and_ensemble_loss(task[1])
            if P_first:
                nested_al[data_seed][P][alpha] = al
                nested_el[data_seed][P][alpha] = el
                nested_num_nan[data_seed][P][alpha] = num_nan
            else:
                nested_al[data_seed][alpha][P] = al
                nested_el[data_seed][alpha][P] = el
                nested_num_nan[data_seed][alpha][P] = num_nan
    return nested_al, nested_el, nested_num_nan


def get_accuracies(results_list, P_first=True):
    nested_al = defaultdict(lambda: defaultdict(dict))
    nested_el = defaultdict(lambda: defaultdict(dict))
    nested_num_nan = defaultdict(lambda: defaultdict(dict))
    for res in results_list:
        data_seed = res['data_config']['data_seed']
        P = res['data_config']['P']
        num_tasks = len(res) - 1
        for i in range(num_tasks):
            task = res[f'task-{i}']
            task_config = task[0]
            alpha = task_config['model_params']['alpha']
            al, el, num_nan = average_and_ensemble_accuracy(task[1])
            if P_first:
                nested_al[data_seed][P][alpha] = al
                nested_el[data_seed][P][alpha] = el
                nested_num_nan[data_seed][P][alpha] = num_nan
            else:
                nested_al[data_seed][alpha][P] = al
                nested_el[data_seed][alpha][P] = el
                nested_num_nan[data_seed][alpha][P] = num_nan
    return nested_al, nested_el, nested_num_nan

def get_train_losses(results_list, P_first=True):
    nested_al = defaultdict(lambda: defaultdict(dict))
    nested_num_nan = defaultdict(lambda: defaultdict(dict))
    for res in results_list:
        data_seed = res['data_config']['data_seed']
        P = res['data_config']['P']
        num_tasks = len(res) - 1
        for i in range(num_tasks):
            task = res[f'task-{i}']
            task_config = task[0]
            alpha = task_config['model_params']['alpha']
            al, num_nan = average_f_train_loss(task[1])
            if P_first:
                nested_al[data_seed][P][alpha] = al
                nested_num_nan[data_seed][P][alpha] = num_nan
            else:
                nested_al[data_seed][alpha][P] = al
                nested_num_nan[data_seed][alpha][P] = num_nan
    return nested_al, nested_num_nan