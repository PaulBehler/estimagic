"""Test many different criterion functions and many sets of constraints.

- only minimize
- only gradient based algorithms scipy_lbfgsb (scalar) and scipy_ls_dogbox (least
  squares)
- closed form and numerical derivatives

"""
import numpy as np
import pandas as pd
import pytest
from estimagic.examples.criterion_functions import rosenbrock_dict_criterion
from estimagic.examples.criterion_functions import rosenbrock_gradient
from estimagic.examples.criterion_functions import (
    rotated_hyper_ellipsoid_dict_criterion,
)
from estimagic.examples.criterion_functions import rotated_hyper_ellipsoid_gradient
from estimagic.examples.criterion_functions import sos_dict_criterion
from estimagic.examples.criterion_functions import sos_gradient
from estimagic.examples.criterion_functions import sos_jacobian
from estimagic.examples.criterion_functions import sos_ls_jacobian
from estimagic.examples.criterion_functions import trid_gradient
from estimagic.examples.criterion_functions import trid_scalar_criterion
from estimagic.optimization.optimize import minimize
from numpy.testing import assert_array_almost_equal as aaae


FUNC_INFO = {
    "sos": {
        "criterion": sos_dict_criterion,
        "gradient": sos_gradient,
        "jacobian": sos_jacobian,
        "ls_jacobian": sos_ls_jacobian,
        "default_result": np.zeros(3),
        "fixed_result": [1, 0, 0],
        "entries": ["value", "contributions", "root_contributions"],
        "linear_result": [0.8, 1.6, 0],
        "probability_result": [0.5, 0.5, 0],
    },
    "rotated_hyper_ellipsoid": {
        "criterion": rotated_hyper_ellipsoid_dict_criterion,
        "gradient": rotated_hyper_ellipsoid_gradient,
        "entries": ["value", "contributions", "root_contributions"],
        "default_result": np.zeros(3),
        "fixed_result": [1, 0, 0],
        "linear_result": [0.571428571, 1.714285714, 0],
        "probability_result": [0.4, 0.6, 0],
    },
    "rosenbrock": {
        "criterion": rosenbrock_dict_criterion,
        "gradient": rosenbrock_gradient,
        "entries": ["value", "contributions"],
        "default_result": np.ones(3),
        "linear_result": "unknown",
        "probability_result": "unknown",
    },
    "trid": {
        "criterion": trid_scalar_criterion,
        "gradient": trid_gradient,
        "entries": ["value"],
        "default_result": [3, 4, 3],
        "fixed_result": [1, 2.666666667, 2.333333333],
        "equality_result": [3, 3, 3],
        "pairwise_equality_result": [3.333333333, 3.333333333, 2.666666667],
        "increasing_result": [2.666666667, 3.3333333, 3.3333333],
        "decreasing_result": "unknown",
        "linear_result": [1.185185185, 1.4074074069999998, 1.703703704],
        "probability_result": [0.272727273, 0.727272727, 1.363636364],
        "covariance_result": "unknown",
        "sdcorr_result": "unknown",
    },
}


CONSTR_INFO = {
    "fixed": [{"loc": [0], "type": "fixed", "value": 1}],
    "equality": [{"loc": [0, 1, 2], "type": "equality"}],
    "pairwise_equality": [{"locs": [0, 1], "type": "pairwise_equality"}],
    "increasing": [{"loc": [1, 2], "type": "increasing"}],
    "decreasing": [{"loc": [0, 1], "type": "decreasing"}],
    "linear": [{"loc": [0, 1], "type": "linear", "value": 4, "weights": [1, 2]}],
    "probability": [{"loc": [0, 1], "type": "probability"}],
    "covariance": [{"loc": [0, 1, 2], "type": "covariance"}],
    "sdcorr": [{"loc": [0, 1, 2], "type": "sdcorr"}],
}


START_INFO = {
    "fixed": [1, 1.5, 4.5],
    "equality": [1, 1, 1],
    "pairwise_equality": [2, 2, 3],
    "increasing": [1, 2, 3],
    "decreasing": [3, 2, 1],
    "linear": [2, 1, 3],
    "probability": [0.8, 0.2, 3],
    "covariance": [2, 1, 2],
    "sdcorr": [2, 2, 0.5],
}

KNOWN_FAILURES = {
    ("rosenbrock", "equality"),
    ("rosenbrock", "decreasing"),  # imprecise
}

test_cases = []
for crit_name in FUNC_INFO:
    for constr_name in CONSTR_INFO:
        unknown_res = FUNC_INFO[crit_name].get(f"{constr_name}_result") == "unknown"
        known_failure = (crit_name, constr_name) in KNOWN_FAILURES
        if not any([unknown_res, known_failure]):
            for deriv in None, FUNC_INFO[crit_name]["gradient"]:
                test_cases.append((crit_name, "scipy_lbfgsb", deriv, constr_name))

            if "root_contributions" in FUNC_INFO[crit_name]["entries"]:
                for deriv in list({FUNC_INFO[crit_name].get("ls_jacobian"), None}):
                    test_cases.append(
                        (crit_name, "scipy_ls_dogbox", deriv, constr_name)
                    )


@pytest.mark.parametrize(
    "criterion_name, algorithm, derivative, constraint_name", test_cases
)
def test_constrained_minimization(
    criterion_name, algorithm, derivative, constraint_name
):

    constraints = CONSTR_INFO[constraint_name]
    criterion = FUNC_INFO[criterion_name]["criterion"]
    params = pd.Series(START_INFO[constraint_name], name="value").to_frame()

    res = minimize(
        criterion=criterion,
        params=params,
        algorithm=algorithm,
        derivative=derivative,
        constraints=constraints,
    )

    calculated = res["solution_params"]["value"].to_numpy()

    expected = FUNC_INFO[criterion_name].get(
        f"{constraint_name}_result", FUNC_INFO[criterion_name]["default_result"]
    )

    aaae(calculated, expected, decimal=4)
