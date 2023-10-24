import pytest
import numpy as np


@pytest.mark.optimised
def test_dot_product_score_equality():
    rng = np.random.RandomState(7)
    n_spots = 2
    n_rounds = 7
    n_genes = 4
    n_channels_use = 3
    spot_colours = rng.rand(n_spots, n_rounds, n_channels_use)
    spot_colours_optimised = spot_colours.reshape(n_spots, -1)
    bled_codes = rng.rand(n_genes, n_rounds, n_channels_use)
    bled_codes_optimised = bled_codes.reshape(n_genes, -1)
    weight_squared = rng.rand(n_spots, n_rounds, n_channels_use)
    weight_squared_optimised = weight_squared.reshape(n_spots, -1)
    norm_shift = rng.rand()
    from coppafish.call_spots.dot_product import dot_product_score
    gene_no, gene_score, gene_score_second = dot_product_score(spot_colours, bled_codes, weight_squared, norm_shift)
    assert gene_no.shape == (n_spots, ), f'Expected `gene_no` to have shape ({n_spots}, )'
    assert gene_score.shape == (n_spots, ), f'Expected `gene_score` to have shape ({n_spots}, )'
    from coppafish.call_spots.dot_product_optimised import dot_product_score
    score = dot_product_score(spot_colours_optimised, bled_codes_optimised, norm_shift, weight_squared_optimised)
    assert score.shape == (n_spots, n_genes), 'Unexpected dot product score shape'
