#!/bin/bash

#SBATCH --job-name=4
#SBATCH -e slurm-%j.err
#SBATCH -o slurm-%j.out
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --mem=128g
#SBATCH --partition=pehlevan_gpu
#SBATCH --ntasks=1       
#SBATCH --gres=gpu:1

module load cuda/11.7.1-fasrc01 cudnn/8.5.0.96_cuda11-fasrc01 Anaconda3/2020.11

source activate gs

mkdir /tmp/4/data-dir
cp -R "/n/holystore01/LABS/pehlevan_lab/Users/sab/cifar-10-batches-py" /tmp/4/data-dir

mkdir /tmp/4/results

cp -R /n/home07/ssainathan/workplace/gpu_scheduler /tmp/4
cd /tmp/4/gpu_scheduler

rm conf/config.yaml

printf "defaults:\n  - experiment: sweep_4" > conf/config.yaml

srun python3 main.py