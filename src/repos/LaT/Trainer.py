"""Select the original per-backbone training strategy inside one project."""

from trainers import CADATrainer, MOELightTrainer, MOETrainer, MTLTrainer, ReLDTrainer


TRAINER_REGISTRY = {
    "MTL": MTLTrainer,
    "MOE": MOETrainer,
    "MOE_LIGHT": MOELightTrainer,
    "CADA": CADATrainer,
    "RELD": ReLDTrainer,
}


class Trainer:
    def __new__(cls, args, env_params, model_params, optimizer_params, trainer_params):
        model_type = args.model_type.upper()
        try:
            trainer_class = TRAINER_REGISTRY[model_type]
        except KeyError as exception:
            raise ValueError("Unsupported unified model type: {}".format(model_type)) from exception
        print(">> Trainer strategy: {}".format(trainer_class.__module__))
        return trainer_class(args, env_params, model_params, optimizer_params, trainer_params)
