import numpy as np
import torch


def dot_product_score(
    spot_colours: np.ndarray | torch.Tensor,
    bled_codes: np.ndarray | torch.Tensor,
) -> np.ndarray | torch.Tensor:
    """
    Score each spot to each gene. The score is a dot product of each round separately, giving each round a similar
    contribution. The maximum score is the assigned gene for said spot. A score is reduced by 1 / n_rounds when the
    spot colour is zero in said round. The scores range from 0 to infinity.

    Args:
        spot_colours (`(n_spots x n_rounds x n_channels_use) ndarray[float]`): spot colours after call spots scaling
            has been applied. They must not be L2 normalised yet.
        bled_codes (`(n_genes x n_rounds x n_channels_use) ndarray[float]`): normalised bled codes.

    Returns:
        (`(n_spots x n_genes) ndarray[float32] or tensor[float32]`): score. score such that `score[d, c]` gives a
            "round dot product" between `spot_colours` vector `d` with `bled_codes` vector `c`. Returns a tensor if
            spot_colours is a tensor.
    """
    assert type(spot_colours) in (np.ndarray, torch.Tensor)
    assert type(bled_codes) in (np.ndarray, torch.Tensor)

    if type(spot_colours) is np.ndarray:
        spot_colours_torch = torch.from_numpy(spot_colours.copy())
    else:
        spot_colours_torch = spot_colours.detach().clone()
    if type(bled_codes) is np.ndarray:
        bled_codes_torch = torch.from_numpy(bled_codes.copy())
    else:
        bled_codes_torch = bled_codes.detach().clone()
    spot_colours_torch = spot_colours_torch.float()
    bled_codes_torch = bled_codes_torch.float()
    assert spot_colours_torch.ndim == bled_codes_torch.ndim == 3
    assert spot_colours_torch.shape[1:] == bled_codes_torch.shape[1:]

    n_rounds = spot_colours_torch.shape[1]

    # Spot colours are divided by their maximum for each round separately.
    spot_colours_torch /= spot_colours_torch.abs().max(2, keepdim=True).values
    # Bled codes are L2 normalised.
    bled_codes_torch /= torch.linalg.vector_norm(bled_codes_torch, dim=2, keepdim=True)

    # Has shape (n_spots x n_genes x n_rounds x n_channels).
    scores = spot_colours_torch[:, np.newaxis] * bled_codes_torch[np.newaxis]
    # Sum over rounds and channels
    scores = scores.sum((2, 3))
    scores /= n_rounds
    # Has shape (n_spots x n_genes).
    scores = scores.abs()

    if type(spot_colours) is np.ndarray:
        scores = scores.numpy()

    return scores


def gene_prob_score(spot_colours: np.ndarray, bled_codes: np.ndarray, kappa: float = 2) -> np.ndarray:
    """
    Probability model says that for each spot in a particular round, the normalised fluorescence vector follows a
    Von-Mises Fisher distribution with mean equal to the normalised fluorescence for each dye and concentration
    parameter kappa. Then invert this to get prob(dye | fluorescence) and multiply across rounds to get
    prob(gene | spot_colours).

    Args:
        spot_colours (`(n_spots x n_rounds x n_channels_use) ndarray`): spot colours.
        bled_codes (`(n_genes x n_rounds x n_channels_use) ndarray`): normalised bled codes.
        kappa (float, optional), scaling factor for dot product score. Default: 2.

    Returns:
        (`(n_spots x n_genes) ndarray[float]`): gene probabilities.
    """
    n_genes = bled_codes.shape[0]
    n_spots, n_rounds, n_channels_use = spot_colours.shape
    # First, normalise spot_colours so that for each spot s and round r, norm(spot_colours[s, r, :]) = 1
    spot_colours = spot_colours / np.linalg.norm(spot_colours, axis=2)[:, :, None]
    # Do the same for bled_codes
    bled_codes = bled_codes / np.linalg.norm(bled_codes, axis=2)[:, :, None]
    # Flip the sign of a single spot and round if spot_colours[s, r, c] < 0 for the greatest magnitude channel.
    spot_colours_reshaped = spot_colours.copy().reshape((-1, n_channels_use))
    negatives = np.take_along_axis(spot_colours_reshaped, np.argmax(spot_colours_reshaped, axis=1)[:, None], 1) < 0
    spot_colours[negatives.reshape((n_spots, n_rounds))] *= -1
    # At this point, reshape spot_colours to be [n_spots, n_rounds * n_channels_use] and bled_codes to be
    # [n_genes, n_rounds * n_channels_use]
    spot_colours = spot_colours.reshape((n_spots, -1))
    bled_codes = bled_codes.reshape((n_genes, -1))
    # Now we can compute the dot products of each spot with each gene, producing a matrix of shape [n_spots, n_genes]
    dot_product = spot_colours @ bled_codes.T
    probability = np.exp(kappa * dot_product)
    # Now normalise so that each row sums to 1
    probability = np.nan_to_num(probability / np.sum(probability, axis=1)[:, None])

    return probability
