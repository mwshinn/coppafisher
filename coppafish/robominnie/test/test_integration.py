import os
import warnings

import pytest

from coppafish import Notebook, Viewer, RegistrationViewer
from coppafish.robominnie.robominnie import Robominnie


def get_robominnie_scores(rm: Robominnie) -> None:
    tile_scores = rm.score_tiles("prob", score_threshold=0.9)
    print(f"Prob scores for each tile: {tile_scores}")
    if any([score < 75 for score in tile_scores]):
        warnings.warn(f"Anchor method contains tile score < 75%")
    if any([score < 40 for score in tile_scores]):
        raise ValueError(f"Anchor method has a tile score < 40%. This can be a sign of a pipeline bug")

    tile_scores = rm.score_tiles("anchor", score_threshold=0.5)
    print(f"Anchor scores for each tile: {tile_scores}")
    if any([score < 75 for score in tile_scores]):
        warnings.warn(f"Anchor method contains tile score < 75%")
    if any([score < 40 for score in tile_scores]):
        raise ValueError(f"Anchor method has a tile score < 40%. This can be a sign of a pipeline bug")

    tile_scores = rm.score_tiles("omp", score_threshold=0.4)
    print(f"OMP scores for each tile: {tile_scores}")
    if any([score < 75 for score in tile_scores]):
        warnings.warn(f"OMP method contains tile score < 75%")
    if any([score < 40 for score in tile_scores]):
        raise ValueError(f"OMP method has a tile score < 40%. This can be a sign of a pipeline bug")


@pytest.mark.integration
def test_integration_small_two_tile():
    """
    Summary of input data: random spots and pink noise.

    Includes anchor round, sequencing rounds, one `4x100x100` tile.

    Returns:
        Notebook: complete coppafish Notebook.
    """
    output_dir = get_output_dir()
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    robominnie = Robominnie(n_channels=5, n_planes=10, tile_sz=128, n_tiles_y=2)
    robominnie.generate_gene_codes()
    robominnie.generate_pink_noise()
    robominnie.add_spots()
    # We add a fake bad tile, round, channel image to make sure it can run through the pipeline.
    robominnie.save_raw_images(output_dir, bad_trcs=[[0, 2, 3]])
    robominnie.run_coppafish()
    get_robominnie_scores(robominnie)
    del robominnie


@pytest.mark.notebook
@pytest.mark.manual
def test_viewers() -> None:
    """
    Make sure the coppafish Viewer and RegistrationViewer is working without crashing.

    Notes:
        - Requires a robominnie instance to have successfully run through first.
    """
    notebook_path = get_notebook_path()
    if not os.path.exists(notebook_path):
        return
    gene_colours_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".integration_dir/gene_colours.csv")
    notebook = Notebook(notebook_path)
    Viewer(notebook, gene_marker_filepath=gene_colours_path)
    RegistrationViewer(notebook, get_config_path())


def get_output_dir() -> str:
    return os.path.dirname(os.path.dirname(get_notebook_path()))


def get_notebook_path() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), ".integration_dir/output_coppafish/notebook")


def get_config_path() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), ".integration_dir/robominnie.ini")


if __name__ == "__main__":
    test_integration_small_two_tile()
    test_viewers()
