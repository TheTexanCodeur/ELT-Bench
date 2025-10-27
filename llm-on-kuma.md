# LLM on KUMA

## Connect to cluster

```
ssh <username>@kuma.hpc.epfl.ch
```

## Create virtual environment

```
module load gcc/13.2.0
module load python/3.11.7-nbrb6p3

python -m venv ~/envs/vllm
source ~/envs/vllm/bin/activate


# upgrade basics
pip install --upgrade pip wheel setuptools

# install PyTorch and vLLM
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
pip install vllm
pip install vllm[flashinfer] #Faster inference with FlashAttention
```

## Create a GPU shell

```
srun -A <your_account> -p h100 --qos=<your_qos> \
     --gres=gpu:1 --cpus-per-task=8 --mem=40G -t 00:30:00 --pty /bin/bash
```

account would be dias  
Example:

```
srun --account=dias --job-name=vllm-test -p h100 --nodes=1 --qos=normal --gres=gpu:1 --cpus-per-task=8 --mem=120G --time=02:00:00 --pty /bin/bash
```

## Download gpt oss 120B model

```
export HF_HOME="/scratch/<username>/hf-cache"
export TRANSFORMERS_CACHE="$HF_HOME"
export HUGGINGFACE_HUB_CACHE="$HF_HOME"
MODEL_DIR="$HF_HOME/gpt-oss-120b"
mkdir -p "$HF_HOME"

pip install -q huggingface_hub

# download the model
huggingface-cli download openai/gpt-oss-120b \
  --local-dir "$HF_HOME/gpt-oss-120b" \
  --local-dir-use-symlinks False
```

## Launch vllm (gpt oss 120B can run on 1GPU)

```
vllm serve "$MODEL_DIR" \
--served-model-name gpt-oss-120b \
--port 8100 

ssh -L 8100:localhost:8100 qsandoz@kuma.hpc.epfl.ch
```

## Second shell on the same node (for reverse tunneling if needed)

```
srun --jobid=$(squeue -u $USER -h -o %i) --overlap --gres=gpu:0 --cpus-per-task=1 --mem=1G --pty /bin/bash

ssh -R 8100:localhost:8100 <username>@kuma.hpc.epfl.ch
```

## On your local machine, run:

```
ssh -L 8000:localhost:8000 <username>@kuma.hpc.epfl.ch
```

Adjust the port numbers if 8000 is already taken.

## Run a pipeline (in the agents/spider-agent folder):

```
python3 run.py --suffix <suffix> --model gpt-oss-120b --example_index <example_index >
```

**Don't forget to cancel the job once you're done using squeue and scancel commands.**
