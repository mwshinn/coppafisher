import tqdm
import inspect
import numpy as np
import numpy.typing as npt
from typing import Union, Dict, List, Optional

from .. import logging


def get_function_name() -> str:
    """
    Get the name of the function that called this function.

    Returns:
        str: function name.
    """
    return str(inspect.stack()[1][3])


def round_any(x: Union[float, npt.NDArray], base: float, round_type: str = "round") -> Union[float, npt.NDArray]:
    """
    Rounds `x` to the nearest multiple of `base` with the rounding done according to `round_type`.

    Args:
        x: Number or array to round.
        base: Rounds `x` to nearest integer multiple of value of `base`.
        round_type: One of the following, indicating how to round `x` -

            - `'round'`
            - `'ceil'`
            - `'floor'`

    Returns:
        Rounded version of `x`.

    Example:
        ```
        round_any(3, 5) = 5
        round_any(3, 5, 'floor') = 0
        ```
    """
    if round_type == "round":
        return base * np.round(x / base)
    elif round_type == "ceil":
        return base * np.ceil(x / base)
    elif round_type == "floor":
        return base * np.floor(x / base)
    else:
        logging.error(
            ValueError(
                f"round_type specified was {round_type} but it should be one of the following:\n" f"round, ceil, floor"
            )
        )


def setdiff2d(array1: npt.NDArray[np.float_], array2: npt.NDArray[np.float_]) -> npt.NDArray[np.float_]:
    """
    Finds all unique elements in `array1` that are also not in `array2`. Each element is appended along the first axis.
    E.g.

    - If `array1` has `[4,0]` twice, `array2` does not have `[4,0]`, returned array will have `[4,0]` once.

    - If `array1` has `[4,0]` twice, `array2` has `[4,0]` once, returned array will not have `[4,0]`.

    Args:
        array1: `float [n_elements1 x element_dim]`.
        array2: `float [n_elements2 x element_dim]`.

    Returns:
        `float [n_elements_diff x element_dim]`.
    """
    set1 = set([tuple(x) for x in array1])
    set2 = set([tuple(x) for x in array2])
    return np.array(list(set1 - set2))


def expand_channels(array: npt.NDArray[np.float_], use_channels: List[int], n_channels: int) -> npt.NDArray[np.float_]:
    """
    Expands `array` to have `n_channels` channels. The `i`th channel from `array` is placed into the new channel index
    `use_channels[i]` in the new array. Any channels unset in the new array are set to zeroes.

    Args:
        array (`[n1 x n2 x ... x n_k x n_channels_use] ndarray[float]`): array to expand.
        use_channels (`list` of `int`): list of channels to use from `array`.
        n_channels (int): Number of channels to expand `array` to.

    Returns:
        (`[n1 x n2 x ... x n_k x n_channels_use] ndarray[float]`): expanded_array copy.
    """
    assert len(use_channels) <= array.shape[-1], "use_channels is greater than the number of channels found in `array`"
    assert n_channels >= array.shape[-1], "Require n_channels >= the number of channels currently in `array`"

    old_array_shape = np.array(array.shape)
    new_array_shape = old_array_shape.copy()
    new_array_shape[-1] = n_channels
    expanded_array = np.zeros(new_array_shape)

    for i, channel in enumerate(use_channels):
        expanded_array[..., channel] = array[..., i]

    return expanded_array


def reed_solomon_codes(n_genes: int, n_rounds: int, n_channels: Optional[int] = None) -> Dict:
    """
    Generates random gene codes based on reed-solomon principle, using the lowest degree polynomial possible for the
    number of genes needed. The `i`th gene name will be `gene_i`. We assume that `n_channels` is the number of unique
    dyes, each dye is labelled between `(0, n_channels]`.

    Args:
        n_genes (int): number of unique gene codes to generate.
        n_rounds (int): number of sequencing rounds.
        n_channels (int, optional): number of channels. Default: same as `n_rounds`.

    Returns:
        Dict (str: str): gene names as keys, gene codes as values.

    Raises:
        ValueError: if all gene codes produced cannot be unique.

    Notes:
        See [wikipedia](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction) for more details.
    """
    if n_channels is None:
        n_channels = n_rounds
    assert n_rounds > 1, "Require at least two rounds"
    assert n_channels > 1, "Require at least two channels"
    assert n_genes > 0, "Require at least one gene"

    verbose = n_genes > 10
    degree = 0
    # Find the smallest degree polynomial required to produce `n_genes` unique gene codes. We use the smallest degree
    # polynomial because this will have the smallest amount of overlap between gene codes
    while True:
        max_unique_codes = int(n_rounds**degree - n_rounds)
        if max_unique_codes >= n_genes:
            break
        degree += 1
        if degree == 20:
            logging.error(ValueError("Polynomial degree required is too large for generating the gene codes"))
    # Create a `degree` degree polynomial, where each coefficient goes between (0, n_rounds] to generate each unique
    # gene code
    codes = dict()
    # Index 0 is for constant, index 1 for linear coefficient, etc..
    most_recent_coefficient_set = np.array(np.zeros(degree + 1))
    for n_gene in tqdm.trange(n_genes, ascii=True, unit="Codes", desc="Generating gene codes", disable=not verbose):
        # Find the next coefficient set that works, which is not just constant across all rounds (like a background
        # code)
        while True:
            # Iterate to next working coefficient set, by mod n_channels addition
            most_recent_coefficient_set[0] += 1
            for i in range(most_recent_coefficient_set.size):
                if most_recent_coefficient_set[i] >= n_channels:
                    # Cycle back around to 0, then add one to next coefficient
                    most_recent_coefficient_set[i] = 0
                    most_recent_coefficient_set[i + 1] += 1
            if np.all(most_recent_coefficient_set[1 : degree + 1] == 0):
                continue
            break
        # Generate new gene code
        new_code = ""
        gene_name = f"gene_{n_gene}"
        for r in range(n_rounds):
            result = 0
            for j in range(degree + 1):
                result += most_recent_coefficient_set[j] * r**j
            result = int(result)
            result %= n_channels
            new_code += str(result)
        # Add new code to dictionary
        codes[gene_name] = new_code
    values = list(codes.values())
    if len(values) != len(set(values)):
        # Not every gene code is unique
        logging.error(
            ValueError(
                f"Could not generate {n_genes} unique gene codes with {n_rounds} rounds/dyes. "
                + "Maybe try decreasing the number of genes or increasing the number of rounds."
            )
        )
    return codes
