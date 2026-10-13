"""SGD environment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from dacbench import AbstractMADACEnv
from dacbench.envs.env_utils import sgd_utils
from dacbench.envs.env_utils.sgd_utils import random_torchvision_loader


def test(
    model,
    loss_function,
    loader,
    batch_size,
    batch_percentage: float = 1.0,
    device="cpu",
):
    """Evaluate given `model` on `loss_function`.

    Percentage defines how much percentage of the data shall be used.
    If nothing given the whole data is used.

    Returns:
        test_losses: Batch validation loss per data point
    """
    nmb_sets = batch_percentage * (len(loader.dataset) / batch_size)
    model.eval()
    test_losses = []
    test_accuracies = []
    i = 0

    with torch.no_grad():
        for data, target in loader:
            d_data, d_target = data.to(device), target.to(device)
            output = model(d_data)
            _, preds = output.max(dim=1)
            test_losses.append(loss_function(output, d_target))
            test_accuracies.append(torch.sum(preds == target) / len(target))
            i += 1
            if i >= nmb_sets:
                break
    return torch.cat(test_losses), torch.tensor(test_accuracies)


def forward_backward(model, loss_function, loader, device="cpu"):
    """Do a forward and a backward pass for given `model` for `loss_function`.

    Returns:
        loss: Mini batch training loss per data point
    """
    model.train()
    (data, target) = next(iter(loader))
    data, target = data.to(device), target.to(device)
    output = model(data)
    loss = loss_function(output, target)
    loss.mean().backward()
    return loss.mean().detach()


def run_epoch(model, loss_function, loader, optimizer, device="cpu"):
    """Run a single epoch of training for given `model` with `loss_function`."""
    last_loss = None
    running_loss = 0
    model.train()
    for data, target in loader:
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = loss_function(output, target)
        loss.mean().backward()
        optimizer.step()
        last_loss = loss
        running_loss += last_loss.mean().item()
    return last_loss.mean().detach(), running_loss / len(loader)


@dataclass
class SGDInstance:
    """SGD Instance."""

    model: torch.nn.Module
    optimizer_type: torch.optim.Optimizer
    optimizer_params: dict
    dataset_path: str
    dataset_name: str
    batch_size: int
    fraction_of_dataset: float
    train_validation_ratio: float
    seed: int


class SGDEnv(AbstractMADACEnv):
    """The SGD DAC Environment implements the problem of dynamically configuring
    the learning rate hyperparameter of a neural network optimizer
    (more specifically, torch.optim.AdamW) for a supervised learning task.
    While training, the model is evaluated after every epoch.

    Actions correspond to learning rate values in [0,+inf[
    For observation space check `observation_space` method docstring.
    For instance space check the `SGDInstance` class docstring
    Reward:
        negative loss of model on test_loader of the instance       if done
        crash_penalty of the instance                               if crashed
        0                                                           otherwise
    """

    metadata = {"render_modes": ["human"]}  # noqa: RUF012

    def __init__(self, config):
        """Init env."""
        super().__init__(config)
        torch.manual_seed(seed=config.get("seed", 0))
        self.epoch_mode = config.get("epoch_mode", True)
        self.device = config.get("device")

        self.learning_rate = None
        self.crash_penalty = config.get("crash_penalty")
        self.loss_function = config.loss_function(**config.loss_function_kwargs)
        self.use_generator = config.get("use_instance_generator")

        # Use default reward function, if no specific function is given
        self.get_reward = config.get("reward_function", self.get_default_reward)

        # Use default state function, if no specific function is given
        self.get_state = config.get("state_method", self.get_default_state)

    def step(self, action: float):
        """Update the parameters of the neural network using the given learning rate lr,
        in the direction specified by AdamW, and if not done (crashed/cutoff reached),
        performs another forward/backward pass (update only in the next step).
        """
        truncated = super().step_()
        info = {}
        if isinstance(action, float):
            action = [action]
        for g in self.optimizer.param_groups:
            g["lr"] = action[0]
            if len(action) > 1:
                g["betas"] = (action[1], 0.999)

        if self.epoch_mode:
            self.loss, self.average_loss = run_epoch(
                self.model,
                self.loss_function,
                self.train_loader,
                self.optimizer,
                self.device,
            )
        else:
            train_args = [
                self.model,
                self.loss_function,
                self.train_loader,
                self.device,
            ]
            self.optimizer.step()
            self.optimizer.zero_grad()
            self.loss = forward_backward(*train_args)

        crashed = (
            not torch.isfinite(self.loss).any()
            or not torch.isfinite(
                torch.nn.utils.parameters_to_vector(self.model.parameters())
            ).any()
        )
        self.loss = self.loss.numpy().item()

        if crashed:
            self._done = True
            return (
                self.get_state(self),
                self.crash_penalty,
                False,
                True,
                info,
            )

        self._done = truncated

        if (
            self.n_steps % len(self.train_loader) == 0 or self._done
        ):  # Calculate validation loss at the end of an epoch
            batch_percentage = 1.0
        else:
            batch_percentage = 0.1

        val_args = [
            self.model,
            self.loss_function,
            self.validation_loader,
            self.instance.batch_size,
            batch_percentage,
            self.device,
        ]
        validation_loss, validation_accuracy = test(*val_args)

        self.validation_loss = validation_loss.mean().detach().numpy()
        self.validation_accuracy = validation_accuracy.mean().detach().numpy()
        if (
            self.min_validation_loss is None
            or self.validation_loss <= self.min_validation_loss
        ):
            self.min_validation_loss = self.validation_loss

        if self._done:
            val_args = [
                self.model,
                self.loss_function,
                self.test_loader,
                self.instance.batch_size,
                1.0,
                self.device,
            ]
            self.test_losses, self.test_accuracies = test(*val_args)

        reward = self.get_reward(self)

        return self.get_state(self), reward, False, truncated, info

    def reset(self, seed=None, options=None):
        """Initialize the neural network, data loaders, etc. for given/random next task.
        Also perform a single forward/backward pass,
        not yet updating the neural network parameters.
        """
        if options is None:
            options = {}
        super().reset_(seed)

        rng = np.random.RandomState(self.initial_seed)

        # Get loaders for instance
        self.datasets, loaders = random_torchvision_loader(
            self.instance.seed,
            self.instance.dataset_path,
            self.instance.dataset_name,
            self.instance.batch_size,
            self.instance.fraction_of_dataset,
            self.instance.train_validation_ratio,
            dataset_config=self.config.dataset_config,
        )
        self.train_loader, self.validation_loader, self.test_loader = loaders

        if self.use_generator:
            (
                self.model,
                self.optimizer_params,
                self.instance.batch_size,
                self.crash_penalty,
            ) = sgd_utils.random_instance(rng, self.datasets)
        else:
            self.model = self.instance.model()
            self.optimizer_params = self.instance.optimizer_params

        self.learning_rate = None
        self.optimizer_type = self.instance.optimizer_type
        self.info = {}
        self._done = False

        self.model.to(self.device)
        self.optimizer: torch.optim.Optimizer = torch.optim.AdamW(
            **self.instance.optimizer_params, params=self.model.parameters()
        )
        self.loss = 0
        self.test_losses = None

        self.validation_loss = 0
        self.validation_accuracy = 0
        self.min_validation_loss = None

        if self.epoch_mode:
            self.average_loss = 0

        return self.get_state(self), {}

    def get_default_reward(self, _) -> float:
        """The default reward function.

        Args:
            _ (_type_): Empty parameter, which can be used when overriding

        Returns:
            float: The calculated reward
        """
        if self.test_losses is not None:
            reward = self.test_losses.sum().item() / len(self.test_loader.dataset)
        else:
            reward = 0.0
        return -reward

    def get_default_state(self, _) -> dict:
        """Default state function.

        Args:
            _ (_type_): Empty parameter, which can be used when overriding

        Returns:
            dict: The current state
        """
        state = {
            "step": self.c_step,
            "loss": self.loss,
            "validation_loss": self.validation_loss,
            "validation_accuracy": self.validation_accuracy,
            "done": self._done,
        }
        if self.epoch_mode:
            state["average_loss"] = self.average_loss

        if self._done and self.test_losses is not None:
            state["test_losses"] = self.test_losses
            state["test_accuracies"] = self.test_accuracies
        return state

    def render(self, mode="human"):
        """Render progress."""
        if mode == "human":
            epoch = 1 + self.c_step // len(self.train_loader)
            epoch_cutoff = self.n_steps // len(self.train_loader)
            batch = 1 + self.c_step % len(self.train_loader)
            print(
                f"prev_lr {self.optimizer.param_groups[0]['lr'] if self.n_steps > 0 else None}, "  # noqa: E501
                f"epoch {epoch}/{epoch_cutoff}, "
                f"batch {batch}/{len(self.train_loader)}, "
                f"batch_loss {self.loss}, "
                f"val_loss {self.validation_loss}"
            )
        else:
            raise NotImplementedError
