import math as maths
import os
from typing import Tuple

import numpy as np
import scipy
import torch
import tqdm

from .. import log, spot_colors, utils
from ..call_spots import background_pytorch
from ..find_spots import detect_torch
from ..omp import coefs_torch, scores_torch, spots_torch
from ..setup import NotebookPage


def run_omp(
    config: dict,
    nbp_file: NotebookPage,
    nbp_basic: NotebookPage,
    nbp_extract: NotebookPage,
    nbp_filter: NotebookPage,
    nbp_register: NotebookPage,
    nbp_register_debug: NotebookPage,
    nbp_call_spots: NotebookPage,
) -> NotebookPage:
    """
    Run orthogonal matching pursuit (omp) on every pixel to determine a coefficient for each gene at each pixel.

    From the OMP coefficients, score every pixel using an expected spot shape. Detect spots using the image of spot
    scores and save all OMP spots with a large enough score.

    See `'omp'` section of `notebook_comments.json` file for description of the variables in the omp page.

    Args:
        - config: Dictionary obtained from `'omp'` section of config file.
        - nbp_file: `file_names` notebook page.
        - nbp_basic: `basic_info` notebook page.
        - nbp_extract: `extract` notebook page.
        - nbp_filter: `filter` notebook page.
        - nbp_call_spots: `call_spots` notebook page.
        - nbp_register: `register` notebook page.
        - nbp_register_debug: `register_debug` notebook page.

    Returns:
        `NotebookPage[omp]` nbp_omp: page containing gene assignments and info for OMP spots.
    """
    assert type(config) is dict
    assert type(nbp_file) is NotebookPage
    assert type(nbp_basic) is NotebookPage
    assert type(nbp_extract) is NotebookPage
    assert type(nbp_filter) is NotebookPage
    assert type(nbp_register) is NotebookPage
    assert type(nbp_register_debug) is NotebookPage
    assert type(nbp_call_spots) is NotebookPage

    log.info("OMP started")
    log.debug(f"{torch.cuda.is_available()=}")
    log.debug(f"{config['force_cpu']=}")

    nbp = NotebookPage("omp")

    # We want exact, reproducible results.
    torch.backends.cudnn.deterministic = True
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    n_genes = nbp_call_spots.bled_codes.shape[0]
    n_rounds_use = len(nbp_basic.use_rounds)
    n_channels_use = len(nbp_basic.use_channels)
    tile_shape: Tuple[int] = nbp_basic.tile_sz, nbp_basic.tile_sz, len(nbp_basic.use_z)
    colour_norm_factor = np.array(nbp_call_spots.colour_norm_factor, dtype=np.float32)
    colour_norm_factor = torch.asarray(colour_norm_factor).float()
    first_tile: int = nbp_basic.use_tiles[0]

    # Results are appended to these arrays.
    spots_local_yxz = torch.zeros((0, 3), dtype=torch.int16)
    spots_tile = torch.zeros(0, dtype=torch.int16)
    spots_gene_no = torch.zeros(0, dtype=torch.int16)
    spots_score = torch.zeros(0, dtype=torch.float16)
    spots_colours = np.zeros((0, n_rounds_use, n_channels_use), dtype=np.float16)

    for t in nbp_basic.use_tiles:
        # STEP 1: Load every registered sequencing round/channel image into memory
        log.debug(f"Loading tile {t} colours")
        tile_computed_on = np.zeros(np.prod(tile_shape), dtype=np.int8)
        colour_image = np.zeros((np.prod(tile_shape), n_rounds_use, n_channels_use), dtype=np.float16)
        yxz_all = [np.linspace(0, tile_shape[i], tile_shape[i], endpoint=False) for i in range(3)]
        yxz_all = np.array(np.meshgrid(*yxz_all, indexing="ij")).reshape((3, -1)).astype(np.int32).T
        batch_size = maths.floor(utils.system.get_available_memory() * 1.3e7 / n_channels_use)
        n_batches = maths.ceil(np.prod(tile_shape) / batch_size)
        device_str = "gpu" if (not config["force_cpu"] and torch.cuda.is_available()) else "cpu"
        postfix = {"tile": t, "device": device_str.upper()}
        for i, r in enumerate(
            tqdm.tqdm(nbp_basic.use_rounds, desc="Loading spot colours", unit="round", postfix=postfix)
        ):
            for j in range(n_batches):
                index_min = j * batch_size
                index_max = (j + 1) * batch_size
                index_max = min(index_max, np.prod(tile_shape))
                batch_spot_colours = spot_colors.base.get_spot_colours_new(
                    nbp_basic,
                    nbp_file,
                    nbp_extract,
                    nbp_register,
                    nbp_register_debug,
                    t,
                    r,
                    yxz=yxz_all[index_min:index_max],
                    dtype=np.float16,
                    force_cpu=config["force_cpu"],
                )
                batch_spot_colours = batch_spot_colours.T
                batch_spot_colours = torch.asarray(batch_spot_colours)
                colour_image[index_min:index_max, i] = batch_spot_colours
                del batch_spot_colours
        log.debug(f"Loading tile {t} colours complete")

        # STEP 2: Compute OMP coefficients on tile subsets.
        # Store the entire tile's coefficient results into one scipy sparse matrix.
        log.debug(f"Compute coefficients, tile {t} started")
        description = f"Computing OMP coefficients"
        coefficients = scipy.sparse.lil_matrix((np.prod(tile_shape), n_genes), dtype=np.float32)
        subset_count = maths.ceil(np.prod(tile_shape) / config["subset_pixels"])
        for j in tqdm.trange(subset_count, desc=description, unit="subset", postfix=postfix):
            index_min = j * config["subset_pixels"]
            index_max = (j + 1) * config["subset_pixels"]
            # Shrink the subset if it is at the end of the tile.
            index_max = min(index_max, np.prod(tile_shape))
            subset_colours = colour_image[index_min:index_max].astype(np.float32)
            subset_colours = torch.asarray(subset_colours)
            if config["colour_normalise"]:
                subset_colours *= colour_norm_factor[[t]]
            bg_coefficients = torch.zeros((subset_colours.shape[0], n_channels_use), dtype=torch.float32)
            bg_codes = torch.repeat_interleave(torch.eye(n_channels_use)[:, None, :], n_rounds_use, dim=1)
            # give background_vectors an L2 norm of 1 so can compare coefficients with other genes.
            bg_codes = bg_codes / torch.linalg.norm(bg_codes, axis=(1, 2), keepdims=True)
            if config["fit_background"]:
                subset_colours, bg_coefficients, bg_codes = background_pytorch.fit_background(subset_colours)
            bg_codes = bg_codes.float()
            bled_codes = nbp_call_spots.bled_codes
            assert (~np.isnan(bled_codes)).all(), "bled codes cannot contain nan values"
            assert np.allclose(np.linalg.norm(bled_codes, axis=(1, 2)), 1), "bled codes must be L2 normalised"
            bled_codes = torch.asarray(bled_codes.astype(np.float32))
            subset_colours = subset_colours.reshape((-1, n_rounds_use * n_channels_use))
            bled_codes = bled_codes.reshape((n_genes, n_rounds_use * n_channels_use))
            bg_codes = bg_codes.reshape((n_channels_use, n_rounds_use * n_channels_use))
            subset_coefficients = coefs_torch.compute_omp_coefficients(
                subset_colours,
                bled_codes,
                maximum_iterations=config["max_genes"],
                background_coefficients=bg_coefficients,
                background_codes=bg_codes,
                dot_product_threshold=config["dp_thresh"],
                dot_product_norm_shift=0.0,
                weight_coefficient_fit=config["weight_coef_fit"],
                alpha=config["alpha"],
                beta=config["beta"],
                force_cpu=config["force_cpu"],
            )
            del subset_colours, bg_coefficients, bg_codes, bled_codes
            subset_coefficients = subset_coefficients.numpy()
            tile_computed_on[index_min:index_max] += 1
            coefficients[index_min:index_max] = subset_coefficients
            del subset_coefficients
        del colour_image
        coefficients = coefficients.tocsr()
        assert (tile_computed_on == 1).all()
        log.debug(f"Compute coefficients, tile {t} complete")

        # STEP 2.5: On the first tile, compute a mean OMP spot from coefficients for score calculations.
        if t == first_tile:
            log.info("Computing OMP spot and mean spot")
            shape_isolation_distance_z = config["shape_isolation_distance_z"]
            if shape_isolation_distance_z is None:
                shape_isolation_distance_z = maths.ceil(
                    config["shape_isolation_distance_yx"] * nbp_basic.pixel_size_xy / nbp_basic.pixel_size_z
                )
            genes_used = []
            n_isolated_count = 0
            mean_spots = torch.zeros((0,) + config["spot_shape"]).double()
            for g in range(n_genes):
                if n_isolated_count >= config["spot_shape_max_spots"]:
                    break
                g_coef_image = torch.asarray(coefficients[:, [g]].toarray()).reshape(tile_shape).float()
                g_isolated_yxz, _ = detect_torch.detect_spots(
                    g_coef_image,
                    config["shape_coefficient_threshold"],
                    config["shape_isolation_distance_yx"],
                    shape_isolation_distance_z,
                    force_cpu=config["force_cpu"],
                )
                g_n_isolated_count = g_isolated_yxz.shape[0]
                n_isolated_count += g_n_isolated_count
                g_mean_spot = spots_torch.compute_mean_spot_from(
                    g_coef_image, g_isolated_yxz, config["spot_shape"], config["force_cpu"]
                )
                mean_spots = torch.concat((mean_spots, g_mean_spot[np.newaxis].double() * g_n_isolated_count), dim=0)
                genes_used.append(g)
                del g_coef_image, g_isolated_yxz, g_n_isolated_count, g_mean_spot
            mean_spot = (mean_spots * len(genes_used) / n_isolated_count).mean(dim=0).float()
            log.debug(f"OMP mean spot computed with {n_isolated_count} isolated spots from genes {genes_used}")
            if n_isolated_count < 10:
                log.warn(f"OMP mean spot computed with only {n_isolated_count} isolated spots")
            del shape_isolation_distance_z, n_isolated_count, genes_used, mean_spots
            spot = torch.zeros_like(mean_spot, dtype=torch.int16)
            spot[mean_spot >= config["shape_sign_thresh"]] = 1
            edge_counts = spots_torch.count_edge_ones(spot)
            if edge_counts > 0:
                log.warn(
                    f"The spot contains {edge_counts} ones on the x/y edges. You may need to increase spot_shape in"
                    + " the OMP config to avoid spot cropping. See _omp.pdf for more detail."
                )
            n_positives = (spot == 1).sum()
            message = f"Computed spot contains {n_positives} strongly positive values."
            if n_positives < 5:
                message += f" You may need to reduce shape_sign_thresh in the OMP config"
                if n_positives == 0:
                    raise ValueError(message)
                log.warn(message)
            else:
                log.debug(message)

            nbp.spot_tile = t
            nbp.mean_spot = np.array(mean_spot)
            nbp.spot = np.array(spot)
            log.info("Computing OMP spot and mean spot complete")

        # TODO: This can be sped up when there is sufficient RAM by running on multiple genes at once.
        for g in tqdm.trange(n_genes, desc=f"Scoring/detecting spots", unit="gene", postfix=postfix):
            # STEP 3: Score every gene's coefficient image.
            g_coef_image = torch.asarray(coefficients[:, [g]].toarray()).float().reshape(tile_shape)
            g_coef_image = g_coef_image[np.newaxis]
            g_scores = scores_torch.score_coefficient_image(
                g_coef_image, spot, mean_spot, config["high_coef_bias"], config["force_cpu"]
            )
            g_scores = g_scores[0].to(torch.float16)
            del g_coef_image

            # STEP 4: Detect genes as score local maxima.
            g_spots_local_yxz, g_spot_scores = detect_torch.detect_spots(
                g_scores,
                config["score_threshold"],
                config["radius_xy"],
                config["radius_z"],
                force_cpu=config["force_cpu"],
            )
            del g_scores
            g_spots_local_yxz = g_spots_local_yxz.to(torch.int16)
            g_spot_scores = g_spot_scores.to(torch.float16)
            n_g_spots = g_spot_scores.size(0)
            if n_g_spots == 0:
                continue
            g_spots_tile = torch.full((n_g_spots,), t).to(torch.int16)
            g_spots_gene_no = torch.full((n_g_spots,), g).to(torch.int16)

            # Add new results.
            spots_local_yxz = torch.cat((spots_local_yxz, g_spots_local_yxz), dim=0)
            spots_score = torch.cat((spots_score, g_spot_scores), dim=0)
            spots_tile = torch.cat((spots_tile, g_spots_tile), dim=0)
            spots_gene_no = torch.cat((spots_gene_no, g_spots_gene_no), dim=0)
            del g_spots_local_yxz, g_spot_scores, g_spots_tile, g_spots_gene_no

        del coefficients
        t_spots = spots_tile == t
        if t_spots.sum() == 0:
            raise ValueError(
                f"No OMP spots found on tile {t}. Please check that registration and call spots is working. "
                + "If so, consider adjusting OMP config parameters."
            )
        # For each detected spot, save the image intensity at its location, without background fitting.
        log.debug(f"Gathering spot colours")
        t_local_yxzs = spots_local_yxz[t_spots].int().numpy()
        t_spots_colours = np.zeros((t_spots.sum(), n_rounds_use, n_channels_use), dtype=np.float16)
        for i, r in enumerate(nbp_basic.use_rounds):
            t_spots_colours[:, i] = spot_colors.base.get_spot_colours_new(
                nbp_basic,
                nbp_file,
                nbp_extract,
                nbp_register,
                nbp_register_debug,
                t,
                r,
                yxz=t_local_yxzs,
                dtype=np.float16,
                force_cpu=config["force_cpu"],
            ).T
        spots_colours = np.append(spots_colours, t_spots_colours, axis=0)
        log.debug(f"Gathering spot colours complete")
        del t_spots, t_local_yxzs, t_spots_colours

    nbp.local_yxz = np.array(spots_local_yxz)
    nbp.scores = np.array(spots_score)
    nbp.tile = np.array(spots_tile)
    nbp.gene_no = np.array(spots_gene_no)
    nbp.colours = spots_colours
    log.info("OMP complete")

    return nbp
