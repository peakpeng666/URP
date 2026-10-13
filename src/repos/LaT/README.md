# LaT: LLM-as-Trainer for Multi-Task Vehicle Routing Solvers

Official research code for **LaT**, a plug-and-play training paradigm that uses a pretrained large language model as an external trainer for multi-task neural vehicle routing solvers.

> Paper: *LaT: LLM-as-Trainer for Multi-Task Vehicle Routing Solvers*

Multi-task VRP solvers share parameters across tasks with different optimization difficulty. LaT periodically summarizes validation performance across all tasks and asks a frozen LLM to produce a stage-wise constraint guidance vector. The vector is combined with the active task constraints and injected into lightweight encoder side branches during subsequent policy optimization.

The LLM does not construct routes, receive gradients, or update solver parameters directly. After training, the final guidance vector is fixed and the LLM is removed, so evaluation requires no LLM API call.

## VRP tasks

The benchmark contains 16 variants formed from five elementary constraints:

- `C`: capacity
- `O`: open route
- `B`: backhaul
- `L`: route-length limit
- `TW`: time window

| Variant | C | O | B | L | TW | Split |
|---|:---:|:---:|:---:|:---:|:---:|---|
| CVRP | ✓ |  |  |  |  | Train |
| OVRP | ✓ | ✓ |  |  |  | Train |
| VRPB | ✓ |  | ✓ |  |  | Train |
| VRPL | ✓ |  |  | ✓ |  | Train |
| VRPTW | ✓ |  |  |  | ✓ | Train |
| OVRPTW | ✓ | ✓ |  |  | ✓ | Train |
| OVRPB | ✓ | ✓ | ✓ |  |  | Zero-shot |
| OVRPL | ✓ | ✓ |  | ✓ |  | Zero-shot |
| VRPBL | ✓ |  | ✓ | ✓ |  | Zero-shot |
| VRPBTW | ✓ |  | ✓ |  | ✓ | Zero-shot |
| VRPLTW | ✓ |  |  | ✓ | ✓ | Zero-shot |
| OVRPBL | ✓ | ✓ | ✓ | ✓ |  | Zero-shot |
| OVRPBTW | ✓ | ✓ | ✓ |  | ✓ | Zero-shot |
| OVRPLTW | ✓ | ✓ |  | ✓ | ✓ | Zero-shot |
| VRPBLTW | ✓ |  | ✓ | ✓ | ✓ | Zero-shot |
| OVRPBLTW | ✓ | ✓ | ✓ | ✓ | ✓ | Zero-shot |

`Train_ALL` jointly trains on the six training variants. `ALL` evaluates all 16 variants, including the ten unseen constraint combinations.


## Installation

Requirements:

- Python 3.8 or later
- PyTorch 1.12 or later
- Git LFS for packaged `.pkl` datasets and checkpoints

```bash
git clone <REPOSITORY_URL>
cd LaT
git lfs install
git lfs pull
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux or macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For GPU training, install the PyTorch build matching the local CUDA toolkit before installing the remaining dependencies.

## Verify the environment

```bash
python lat.py list
python lat.py doctor
```

## Reproduce paper training

The paper trains separate models for `N=50` and `N=100` with the following schedule:

| Setting | Value |
|---|---:|
| Epochs | 5,000 |
| Training instances per epoch | 20,000 |
| Batch size | 128 |
| Validation interval | 50 epochs |
| LLM guidance update interval | 500 epochs |
| Validation-history length | 5 records |
| External trainer | GLM-5.1 |

Set the LLM API key before training.

Windows PowerShell:

```powershell
$env:LLM_CONTROL_API_KEY="your-api-key"
```

Linux or macOS:

```bash
export LLM_CONTROL_API_KEY="your-api-key"
```

Example for 50-node LaT-POMO-MTL:

```bash
python train.py \
  --model_type MTL \
  --problem Train_ALL \
  --problem_size 50 \
  --pomo_size 50 \
  --epochs 5000 \
  --train_episodes 20000 \
  --train_batch_size 128 \
  --validation_interval 50 \
  --control_update_interval 500 \
  --control_injection encoder_all \
  --llm_control \
  --llm_control_model glm-5.1 \
  --llm_control_base_url https://open.bigmodel.cn/api/paas/v4
```

Run the same configuration with `--problem_size 100 --pomo_size 100` for the 100-node setting.

Select another paper backbone with one of:

```bash
python train.py --model_type MOE       --problem Train_ALL --problem_size 50 --pomo_size 50
python train.py --model_type MOE_LIGHT --problem Train_ALL --problem_size 50 --pomo_size 50
python train.py --model_type CADA      --problem Train_ALL --problem_size 50 --pomo_size 50
python train.py --model_type RELD      --problem Train_ALL --problem_size 50 --pomo_size 50 --ffidt
```

MOE and MOE_LIGHT retain their expert-routing options. ReLD uses `--ffidt` by default. Run `python train.py --help` for all architecture and optimization parameters.

Training outputs are written to:

```text
results/<model_type>/<run_id>/
```

The LLM controller falls back to statistical guidance if the endpoint is unavailable. A valid LLM endpoint and API key are therefore required to reproduce the paper's LLM-guided experiments.

## Evaluation

Evaluation does not require an LLM API key. Use a checkpoint trained with the matching backbone, architecture, and problem size.

```bash
python test.py \
  --model_type MTL \
  --checkpoint results/mtl/<run_id>/epoch-5000.pt \
  --problem ALL \
  --problem_size 50 \
  --pomo_size 50 \
  --test_episodes 1000 \
  --aug_factor 8
```

Other backbones:

```bash
python test.py --model_type MOE       --checkpoint results/moe/<run_id>/epoch-5000.pt
python test.py --model_type MOE_LIGHT --checkpoint results/moe_light/<run_id>/epoch-5000.pt
python test.py --model_type CADA      --checkpoint results/cada/<run_id>/epoch-5000.pt
python test.py --model_type RELD      --checkpoint results/reld/<run_id>/epoch-5000.pt
```

Checkpoint metadata is validated to prevent loading a different backbone. Legacy CaDA and ReLD checkpoints recorded as `MTL` remain supported.

Run `python test.py --help` for custom datasets, augmentation, sampling, fine-tuning, and benchmark options.



## Data

The shared `data/` directory contains generated VRP instances, reference solutions, CVRPLIB Set-X instances, and Solomon VRPTW instances.

Generate random instances with:

```bash
python generate_data.py --problem ALL --problem_size 50 --num_samples 1000 --no_cuda
```

Generated instances do not include the reference solutions required for relative-gap evaluation.



## License

See [LICENSE](LICENSE).
