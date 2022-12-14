from dataclasses import dataclass, field
from omegaconf import MISSING
# from hydra.core.config_store import ConfigStore

@dataclass
class TrainingParams:
    eta_0: float = 0.1
    momentum: float = 0.9
    weight_decay: float = 1e-5 # TODO: not implemented; replace with batch_size
    batch_size: int = 128
    epochs: int = 80
    full_batch_gradient: bool = False


@dataclass
class DataParams:
    P: int = MISSING
    k: int = 0 # no target fn
    on_device: bool = True
    random_subset: bool = True
    data_seed: int = MISSING
    root_dir: str = 'data-dir'


@dataclass
class ModelParams:
    N: int = 100
    alpha: float = 1.0


@dataclass
class TaskConfig:
    training_params: TrainingParams = field(default_factory=TrainingParams)
    model_params: ModelParams = field(default_factory=ModelParams)
    repeat: int = 12
    parallelize: bool = True
    seed: int = MISSING


@dataclass
class TaskListConfig:
    task_list: list[TaskConfig] = field(default_factory=list)
    data_params: DataParams = field(default_factory=DataParams)

@dataclass
class Setting:
  dataset: str = 'cifar10'
  model: str = 'resnet18'

@dataclass
class Config:
    setting: Setting
    hyperparams: TaskListConfig
    base_dir: str = ''


# def conf_register() -> None:
#     cs = ConfigStore.instance()
#     cs.store(group='hyperparams', name='base-tasks', node=TaskListConfig) # replace node
#     cs.store(group='setting', name='base-cifar10-resnet', node=Setting)
#     cs.store(name='base-config', node=Config)