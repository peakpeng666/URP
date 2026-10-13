"""Select the original per-backbone evaluation strategy inside one project."""

from testers import CADATester, MOELightTester, MOETester, MTLTester, ReLDTester


TESTER_REGISTRY = {
    "MTL": MTLTester,
    "MOE": MOETester,
    "MOE_LIGHT": MOELightTester,
    "CADA": CADATester,
    "RELD": ReLDTester,
}


class Tester:
    def __new__(cls, args, env_params, model_params, tester_params):
        model_type = args.model_type.upper()
        try:
            tester_class = TESTER_REGISTRY[model_type]
        except KeyError as exception:
            raise ValueError("Unsupported unified model type: {}".format(model_type)) from exception
        print(">> Tester strategy: {}".format(tester_class.__module__))
        return tester_class(args, env_params, model_params, tester_params)
