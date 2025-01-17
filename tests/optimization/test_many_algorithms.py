"""Test all availabl algorithms on a simple sum of squares function.

- only minimize
- only numerical derivative

"""
import inspect
import sys

import numpy as np
import pandas as pd
import pytest
from estimagic.examples.criterion_functions import sos_dict_criterion
from estimagic.optimization import AVAILABLE_ALGORITHMS
from estimagic.optimization import GLOBAL_ALGORITHMS
from estimagic.optimization.optimize import minimize
from numpy.testing import assert_array_almost_equal as aaae


LOCAL_ALGORITHMS = {
    key: value
    for key, value in AVAILABLE_ALGORITHMS.items()
    if key not in GLOBAL_ALGORITHMS and key != "bhhh"
}

GLOBAL_ALGORITHMS_AVAILABLE = [
    name for name in AVAILABLE_ALGORITHMS if name in GLOBAL_ALGORITHMS
]

BOUNDED_ALGORITHMS = []
for name, func in LOCAL_ALGORITHMS.items():
    arguments = list(inspect.signature(func).parameters)
    if "lower_bounds" in arguments and "upper_bounds" in arguments:
        BOUNDED_ALGORITHMS.append(name)


@pytest.mark.parametrize("algorithm", LOCAL_ALGORITHMS)
def test_algorithm_on_sum_of_squares(algorithm):
    params = pd.DataFrame()
    params["value"] = [1, 2, 3]

    res = minimize(
        criterion=sos_dict_criterion,
        params=params,
        algorithm=algorithm,
    )

    assert res["success"] in [True, None]
    aaae(res["solution_params"]["value"].to_numpy(), np.zeros(3), decimal=4)


@pytest.mark.parametrize("algorithm", BOUNDED_ALGORITHMS)
def test_algorithm_on_sum_of_squares_with_binding_bounds(algorithm):
    params = pd.DataFrame()
    params["value"] = [3, 2, -3]
    params["lower_bound"] = [1, np.nan, np.nan]
    params["upper_bound"] = [np.nan, np.nan, -1]

    res = minimize(
        criterion=sos_dict_criterion,
        params=params,
        algorithm=algorithm,
    )

    assert res["success"] in [True, None]
    aaae(res["solution_params"]["value"].to_numpy(), np.array([1, 0, -1]), decimal=3)


skip_msg = (
    "The very slow tests of global algorithms are only run on linux which always "
    "runs much faster in continuous integration."
)


@pytest.mark.skipif(sys.platform != "linux", reason=skip_msg)
@pytest.mark.parametrize("algorithm", GLOBAL_ALGORITHMS_AVAILABLE)
def test_global_algorithms_on_sum_of_squares(algorithm):
    params = pd.DataFrame()
    params["value"] = [0.35, 0.35]
    params["lower_bound"] = [0.2, -0.5]
    params["upper_bound"] = [1, 0.5]
    res = minimize(
        criterion=sos_dict_criterion,
        params=params,
        algorithm=algorithm,
    )
    assert res["success"] in [True, None]
    aaae(res["solution_params"]["value"].to_numpy(), np.array([0.2, 0]), decimal=1)
