from pathlib import Path

import gif
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytask
import seaborn as sns
import statsmodels.formula.api as sm
from scipy.optimize import minimize

plt.style.use("dark_background")

gif.options.matplotlib["dpi"] = 200

OUT = Path(__file__).resolve().parent.parent / "source" / "_static" / "images"
PRESENTATIONS = (
    Path(__file__).resolve().parent.parent.parent.parent / "estimagic_presentations"
)
OUT_PRESENTATIONS = PRESENTATIONS / "src" / "figures-generated-from-estimagic-docs"


# ======================================================================================
# Define example function
# ======================================================================================

WEIGHTS = [
    9.003014962148157,
    -3.383000146393776,
    -0.6037887934635748,
    1.6984454347036886,
    -0.9447426232680957,
    0.2669069434366247,
    -0.04446368897497234,
    0.00460781796708519,
    -0.0003000790127508276,
    1.1934114174145725e-05,
    -2.6471293419570505e-07,
    2.5090819960943964e-09,
]


def example_criterion(x):
    x = _unpack_x(x)
    exponents = np.arange(len(WEIGHTS))
    return WEIGHTS @ x ** exponents


def example_gradient(x):
    x = _unpack_x(x)
    exponents = np.arange(len(WEIGHTS))
    return (WEIGHTS * exponents) @ x ** (exponents - 1).clip(0)


def example_hessian(x):
    x = _unpack_x(x)
    exponents = np.arange(len(WEIGHTS))
    return (WEIGHTS * exponents * (exponents - 1)) @ x ** (exponents - 2).clip(0)


def _unpack_x(x):
    if hasattr(x, "__len__"):
        assert len(x) == 1

    if isinstance(x, pd.DataFrame):
        res = x["value"].to_numpy()[0]
    elif isinstance(x, pd.Series):
        res = x.to_numpy()[0]
    elif isinstance(x, (np.ndarray, list, tuple)):
        res = x[0]
    else:
        res = float(x)
    return res


# ======================================================================================
# Define tools
# ======================================================================================


def minimize_with_history(fun, x0, method, jac=None, hess=None):
    """Dumbed down scipy minimize that returns full history.

    This is really only meant for illustration in this notebook. In particular,
    the following restrictions apply:

    - Only works for 1 dimensional problems
    - does not support all arguments

    """
    history = []

    def wrapped_fun(x, history=history):
        history.append(_unpack_x(x))
        return fun(x)

    res = minimize(wrapped_fun, x0, method=method, jac=jac, hess=hess)
    res.history = history
    return res


def plot_function():
    x_grid = np.linspace(0, 20, 100)
    y_grid = [example_criterion(x) for x in x_grid]
    fig, ax = plt.subplots()
    sns.lineplot(x=x_grid, y=y_grid, ax=ax)
    sns.despine()
    return fig, ax


# ======================================================================================
# Define self explaining stylized optimizers
# ======================================================================================


def _generate_stylized_line_search_data():
    remarks = [
        "Initial evaluation: Large gradient, low curvature: Make a big step.",
        "Iteration 1: Large gradient, large curvature: Make a smaller step.",
        "Iteration 2: Very small gradient, low curvature: Make a very small step.",
        "Iteration 3: Very small gradient, low curvature: Make a very small step.",
        "Iteration 4: Medium-sized gradient, low curvature: Make a larger step again.",
        "Iteration 5: Medium-sized gradient, larger curvature: Make a small step.",
        "Iteration 6: Reverse direction due to sign switch in gradient ",
        "Convergence because gradient is approximately zero",
    ]

    x = 2
    data = []
    for remark in remarks:
        f_val = example_criterion(x)
        grad_val = example_gradient(x)
        hess_val = np.clip(example_hessian(x), 0.1, np.inf)
        base_step = -1 / hess_val * grad_val

        aux_line = {
            "x": [x - 2, x, x + 2],
            "y": [f_val - 2 * grad_val, f_val, f_val + 2 * grad_val],
        }

        new_value = np.inf
        evaluated_x = [x]
        evaluated_y = [f_val]
        alpha = 1
        while new_value >= f_val:
            new_x = x + alpha * base_step
            new_value = example_criterion(new_x)
            evaluated_x.append(new_x)
            evaluated_y.append(new_value)

        iteration_data = {
            "evaluated_x": evaluated_x,
            "new_x": new_x,
            "remark": remark,
            "aux_line": aux_line,
        }

        data.append(iteration_data)
        x = new_x
    return data


def _generate_stylized_direct_search_data():
    remarks = [
        (
            "Initial evaluation: candidate value worse than original value. "
            "Do not accept candidate value, switch direction."
        ),
        (
            "Iteration 1: candidate value better than original value. "
            "Accept candidate value, increase step length."
        ),
        (
            "Iteration 2: candidate value better than original value. "
            "Accept candidate value, increase step length."
        ),
        (
            "Iteration 3: candidate value worse than original value. "
            "Do not accept new point, make step smaller."
        ),
        (
            "Iteration 4: Will eventually converge around here. "
            "From iteration 3 we know that we will do worse further right."
        ),
    ]

    data = []
    x = 2
    for i, remark in enumerate(remarks):
        if i == 0:
            other = x - 2
        elif i <= 3:
            other = x + i + 1
        else:
            other = x + 2

        evaluated_x = [x, other]
        evaluated_y = [example_criterion(x), example_criterion(other)]
        argmin_index = np.argmin(evaluated_y)
        new_x = evaluated_x[argmin_index]

        iteration_data = {
            "evaluated_x": [x, other],
            "new_x": new_x,
            "remark": remark,
        }
        data.append(iteration_data)
        x = new_x

    return data


def _generate_stylized_gradient_based_trust_region_data():
    remarks = [
        "Actual vs. expected improvement is large. Accept point, increase radius",
        "Actual vs. expected improvement < 1 but large. Accept point, increase radius.",
        "Actual vs. expected improvement is negative. Reject point, decrease radius.",
        "Actual vs. expected improvement is around 1. Accept point, increase radius.",
        "Actual vs. expected improvement is around 1. Accept point, increase radius.",
        "Convergence because gradient norm is close to zero.",
    ]

    data = []
    x = 2
    radius = 2
    for i, remark in enumerate(remarks):
        if i == 0:
            pass
        elif i <= 2:
            radius += 1
        elif i == 3:
            radius = 2
        else:
            radius += 1

        aux_x = list(np.linspace(x - radius, x + radius, 50))
        aux_y = [_taylor_expansion(point, x) for point in aux_x]

        new_x = aux_x[np.argmin(aux_y)]

        iteration_data = {
            "evaluated_x": [x],
            "new_x": new_x,
            "remark": remark,
            "aux_line": {"x": aux_x, "y": aux_y},
        }

        data.append(iteration_data)
        x = new_x

    return data


def _generate_stylized_gradient_free_trust_region_data():
    remarks = [
        "Actual vs. expected improvement is large. Accept point, increase radius.",
        "Actual vs. expected improvement is large. Accept point, increase radius.",
        (
            "Actual vs. expected improvement is large but step length is small. "
            "Accept point, decrease radius."
        ),
        (
            "Actual vs. expected improvement is reasonable but step length is small. "
            "Accept point, decrease radius."
        ),
        (
            "Actual vs. expected improvement large but absolute improvement is small. "
            "Accept new point but decrease radius"
        ),
        "Absolute improvement is small. Accept new point but decrease radius.",
        "Convergence because trust region radius shrinks to zero.",
    ]

    data = []
    x = 2
    radius = 2
    for i, remark in enumerate(remarks):
        if i == 0:
            pass
        elif i <= 2:
            radius += 1
        else:
            radius = max(0.1, radius - 1)

        aux_x = list(np.linspace(x - radius, x + radius, 50))
        aux_y = [_regression_surrogate(point, x, radius) for point in aux_x]

        new_x = aux_x[np.argmin(aux_y)]

        iteration_data = {
            "evaluated_x": [x],
            "new_x": new_x,
            "remark": remark,
            "aux_line": {"x": aux_x, "y": aux_y},
        }

        data.append(iteration_data)
        x = new_x

    return data


def _taylor_expansion(x, x0):
    """Evaluate taylor expansion around x0 at x."""
    x = _unpack_x(x)
    x0 = _unpack_x(x0)
    f = example_criterion(x0)
    f_prime = example_gradient(x0)
    f_double_prime = example_hessian(x0)

    diff = x - x0
    res = f + f_prime * diff + f_double_prime * 0.5 * diff ** 2
    return res


def _regression_surrogate(x, x0, radius):
    """Evaluate a regression based surrogate model at x.

    x0 and radius define the trust region in which evaluation points are sampled.

    """
    x = _unpack_x(x)
    x0 = _unpack_x(x0)
    deviations = [-radius, 0, radius]

    evaluations = [example_criterion(x0 + deviation) for deviation in deviations]
    df = pd.DataFrame()
    df["x"] = deviations
    df["y"] = evaluations
    params = sm.ols(formula="y ~ x + I(x**2)", data=df).fit().params
    vec = np.array([1, (x - x0), (x - x0) ** 2])
    return params @ vec


# ======================================================================================
# Make convergence gifs
# ======================================================================================

ALGORITHMS = ["Cobyla", "L-BFGS-B", "Nelder-Mead", "trust-ncg"]

PARAMETRIZATON = [
    (
        {
            # Only use first frame since N iterations is unknown
            **(
                {"00": OUT_PRESENTATIONS / f"{algo.lower()}" / f"iteration-00.svg"}
                if PRESENTATIONS.exists()
                else {}
            ),
            **{"gif": OUT / f"history-{algo.lower()}.gif"},
        },
        algo,
    )
    for algo in ALGORITHMS
]


@pytask.mark.parametrize("produces, algorithm", PARAMETRIZATON)
def task_create_convergence_gif(produces, algorithm):
    start_x = np.array([2])
    hessian = example_hessian if algorithm == "trust-ncg" else NotImplementedError
    res = minimize_with_history(
        example_criterion, start_x, method=algorithm, jac=example_gradient, hess=hessian
    )

    # repeat the last point to show it longer in the gif
    points = res.history + [res.history[-1]] * 2

    @gif.frame
    def _plot_history(points, i, produces):
        fig, ax = plot_function()
        sns.rugplot(points, ax=ax)
        plt.plot(
            points[-1],
            example_criterion(points[-1]),
            marker="*",
        )
        sns.despine()
        if "00" in produces:
            plt.savefig(
                str(produces["00"].absolute()).replace(
                    "iteration-00.svg", f"iteration-{i:02d}.svg"
                )
            )

    frames = [_plot_history(points[: i + 1], i, produces) for i in range(len(points))]

    gif.save(frames, produces["gif"], duration=2.5, unit="s")


# ======================================================================================
# Make explanation gifs
# ======================================================================================
STYLIZED_ALGORITHMS = {
    "direct-search": _generate_stylized_direct_search_data(),
    "line-search": _generate_stylized_line_search_data(),
    "gradient-based-trust-region": _generate_stylized_gradient_based_trust_region_data(),
    "gradient-free-trust-region": _generate_stylized_gradient_free_trust_region_data(),
}

PARAMETRIZATON = [
    (
        {
            **{
                i: OUT_PRESENTATIONS / f"stylized-{algo}" / f"iteration-{i:02d}.svg"
                for i in range(len(plot_data))
                if PRESENTATIONS.exists()
            },
            **{"gif": OUT / f"stylized-{algo}.gif"},
        },
        plot_data,
    )
    for algo, plot_data in STYLIZED_ALGORITHMS.items()
]


@pytask.mark.parametrize("produces, plot_data", PARAMETRIZATON)
def task_create_stylized_algo_gif(produces, plot_data):
    # repeat the last point to show it longer in the gif
    plot_data = plot_data + [plot_data[-1]] * 2

    @gif.frame
    def visualize_step(evaluated_x, new_x, aux_line=None, remark=None, i=None):
        fig, ax = plot_function()
        sns.rugplot(x=evaluated_x)
        ax.plot([new_x], [example_criterion(new_x)], marker="*")
        if aux_line is not None:
            sns.lineplot(x=aux_line["x"], y=aux_line["y"])
        if remark is not None:
            plt.subplots_adjust(bottom=0.25)
            plt.figtext(
                0.5,
                0.05,
                remark,
                multialignment="center",
                ha="center",
                wrap=True,
                fontsize=14,
                bbox={
                    "facecolor": "black",
                    "alpha": 0.05,
                    "pad": 5,
                    "edgecolor": "black",  # "#ffffff00",
                },
            )
        if i in produces:
            plt.savefig(produces[i])

    frames = [visualize_step(**data, i=i) for i, data in enumerate(plot_data)]

    gif.save(frames, produces["gif"], duration=7.5, unit="s")


@pytask.mark.skipif(
    not PRESENTATIONS.exists(),
    reason="Not building things in estimagic_presentations because directory is not there.",
)
@pytask.mark.produces(
    OUT_PRESENTATIONS / "example-function.svg"
)
def task_plot_bare_function(produces):
    fig, ax = plot_function()
    plt.savefig(produces)
