import os
from typing import Tuple

from . import basic_info
from . import extract_run
from . import filter_run
from . import find_spots
from . import register
from . import stitch
from . import get_reference_spots
from . import call_reference_spots
from . import omp_torch
from .. import log, setup
from ..find_spots import check_spots
from ..pdf.base import BuildPDF
from ..setup import Notebook, NotebookPage, file_names
from ..utils import system as utils_system
from ..utils import warnings as utils_warnings


def run_pipeline(config_file: str) -> Notebook:
    """
    Run every step of the pipeline.

    Args:
        - config_file (str): path to config file.

    Returns:
        Notebook: notebook containing all information gathered during the pipeline.
    """
    # TODO: We do not need so many functions for running the pipeline.
    nb, nbp_file = initialize_nb(config_file)
    log.error_catch(run_extract, nb, nbp_file)
    log.error_catch(BuildPDF, nb, nbp_file)
    log.error_catch(run_filter, nb, nbp_file)
    log.error_catch(BuildPDF, nb, nbp_file)
    log.error_catch(run_find_spots, nb)
    log.error_catch(run_register, nb, nbp_file)
    log.error_catch(BuildPDF, nb, nbp_file)
    log.error_catch(check_spots.check_n_spots, nb)
    log.error_catch(run_stitch, nb, nbp_file)
    log.error_catch(run_reference_spots, nb, nbp_file)
    log.error_catch(BuildPDF, nb, nbp_file)
    log.error_catch(run_omp, nb, nbp_file)
    log.error_catch(BuildPDF, nb, nbp_file, auto_open=True)
    log.info(f"Pipeline complete", force_email=True)
    return nb


def initialize_nb(config_path: str) -> Tuple[Notebook, NotebookPage]:
    """
    Creates a `Notebook` and adds `basic_info` page before saving.
    `file_names` page will be added automatically as soon as `basic_info` page is added.
    If `Notebook` already exists and contains these pages, it will just be returned.

    Args:
        config_file: Path to config file.

    Returns:
        - `Notebook` containing `basic_info` page.
        - `file_names` notebook page.
    """
    config = setup.config.get_config(config_path)
    config_file = config["file_names"]
    config_notify = config["notifications"]

    nb_path = os.path.join(config_file["output_dir"], config_file["notebook_name"])
    nb = Notebook(nb_path, config_path)

    log.base.set_log_config(
        config_notify["minimum_print_severity"],
        os.path.join(config_file["output_dir"], config_notify["log_name"]),
        config_notify["email_me"],
        config_notify["sender_email"],
        config_notify["sender_email_password"],
    )
    log.info(
        f" COPPAFISH v{utils_system.get_software_version()} ".center(utils_system.current_terminal_size_xy(-33)[0], "=")
    )
    log.base.log_package_versions()

    if utils_system.get_software_version() not in nb.get_unqiue_versions():
        log.warn(
            f"You are running on v{utils_system.get_software_version()}, but the notebook contains "
            + f"data from versions {', '.join(set(nb.get_all_variable_instances(nb._SOFTWARE_VERSION)))}.",
        )
    online_version = utils_system.get_remote_software_version()
    if online_version != utils_system.get_software_version():
        log.warn(
            f"You are running v{utils_system.get_software_version()}. The latest online version is v{online_version}"
        )
    if not nb.has_page("basic_info"):
        nbp_basic = basic_info.set_basic_info_new(config)
        nb += nbp_basic
    else:
        log.warn(utils_warnings.NotebookPageWarning("basic_info"))
    nbp_file = file_names.get_file_names(nb.basic_info, config_path)
    return nb, nbp_file


def run_extract(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    This runs the `extract_and_filter` step of the pipeline to produce the tiff files in the tile directory.

    `extract` and pages are added to the `Notebook` before saving.

    If `Notebook` already contains these pages, it will just be returned.

    Args:
        - nb (Notebook): notebook containing `basic_info` and `scale` pages.
        - nbp_file (NotebookPage): `file_names` page.

    Returns:
        `(n_rounds x n_channels x nz x ny x nx) ndarray[uint16]` or None: all extracted images if running on a single
            tile, otherwise None.
    """
    if not nb.has_page("extract"):
        config = setup.config.get_config(nb.config_path)
        nbp = extract_run.run_extract(config["extract"], nbp_file, nb.basic_info)
        nb += nbp
    else:
        log.warn(utils_warnings.NotebookPageWarning("extract"))


def run_filter(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    Run `filter` step of the pipeline to produce filtered images in the tile directory.

    Args:
        - nb (Notebook): `Notebook` containing `basic_info`, `scale` and `extract` pages.
        - nbp_file (NotebookPage): `file_names` notebook page.
    """
    if not nb.has_page("filter"):
        config = setup.config.get_config(nb.config_path)
        nbp, nbp_debug = filter_run.run_filter(config["filter"], nbp_file, nb.basic_info)
        nb += nbp
        nb += nbp_debug
    else:
        log.warn(utils_warnings.NotebookPageWarning("filter"))


def run_find_spots(nb: Notebook) -> Notebook:
    """
    This runs the `find_spots` step of the pipeline to produce point cloud from each tiff file in the tile directory.

    `find_spots` page added to the `Notebook` before saving if image_t is not given.

    If `Notebook` already contains this page, it will just be returned.

    Args:
        - nb (Notebook): `Notebook` containing `extract` page.

    Returns:
        NoteBook containing 'find_spots' page.
    """
    if not nb.has_page("find_spots"):
        config = setup.config.get_config(nb.config_path)
        nbp = find_spots.find_spots(
            config["find_spots"],
            nb.basic_info,
            nb.filter,
            nb.filter.auto_thresh,
        )
        nb += nbp
    else:
        log.warn(utils_warnings.NotebookPageWarning("find_spots"))
    return nb


def run_stitch(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    This runs the `stitch` step of the pipeline to produce origin of each tile
    such that a global coordinate system can be built. Also saves stitched DAPI and reference channel images.

    `stitch` page added to the `Notebook` before saving.

    If `Notebook` already contains this page, it will just be returned.
    If stitched images already exist, they won't be created again.

    Args:
        - nb (Notebook): `Notebook` containing `find_spots` page.
        - nbp_file (NotebookPage): `file_names` notebook page.
    """
    config = setup.config.get_config(nb.config_path)
    if not nb.has_page("stitch"):
        nbp = stitch.stitch(config["stitch"], nb.basic_info, nbp_file, nb.filter)
        nb += nbp
    else:
        log.warn(utils_warnings.NotebookPageWarning("stitch"))


def run_register(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    This runs the `register_initial` step of the pipeline to find shift between ref round/channel to each imaging round
    for each tile. It then runs the `register` step of the pipeline which uses this as a starting point to get
    the affine transforms to go from the ref round/channel to each imaging round/channel for every tile.

    `register_initial`, `register` and `register_debug` pages are added to the `Notebook` before saving.

    If `Notebook` already contains these pages, it will just be returned.

    Args:
        - (Notebook) nb: notebook containing `extract` page.
        - (NotebookPage) nbp_file: `file_names` notebook page.
    """
    config = setup.config.get_config(nb.config_path)
    # if not all(nb.has_page(["register", "register_debug"])):
    if not nb.has_page("register"):
        nbp, nbp_debug = register.register(
            nb.basic_info,
            nbp_file,
            nb.filter,
            nb.find_spots,
            config["register"],
        )
        # register.preprocessing.generate_reg_images(nb, nbp, nbp_debug)
        nb += nbp
        nb += nbp_debug
    else:
        log.warn(utils_warnings.NotebookPageWarning("register"))
        log.warn(utils_warnings.NotebookPageWarning("register_debug"))


def run_reference_spots(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    This runs the `reference_spots` step of the pipeline to get the intensity of each spot on the reference
    round/channel in each imaging round/channel. The `call_spots` step of the pipeline is then run to produce the
    `bleed_matrix`, `bled_code` for each gene and the gene assignments of the spots on the reference round.

    `ref_spots` and `call_spots` pages are added to the Notebook before saving.

    If `Notebook` already contains these pages, it will just be returned.

    Args:
        - nb: `Notebook` containing `stitch` and `register` pages.
        - nbp_file (NotebookPage): `file_names` notebook page.
    """
    if not nb.has_page("ref_spots"):
        nbp_ref_spots = get_reference_spots.get_reference_spots(
            nbp_basic=nb.basic_info,
            nbp_filter=nb.filter,
            nbp_find_spots=nb.find_spots,
            nbp_register=nb.register,
            nbp_stitch=nb.stitch,
        )
        nb += nbp_ref_spots
    else:
        log.warn(utils_warnings.NotebookPageWarning("ref_spots"))
    if not nb.has_page("call_spots"):
        config = setup.config.get_config(nb.config_path)
        nbp_call_spots = call_reference_spots.call_reference_spots(
            config=config["call_spots"],
            nbp_ref_spots=nb.ref_spots,
            nbp_file=nbp_file,
            nbp_basic=nb.basic_info,
        )
        nb += nbp_call_spots
    else:
        log.warn(utils_warnings.NotebookPageWarning("call_spots"))


def run_omp(nb: Notebook, nbp_file: NotebookPage) -> None:
    """
    This runs the orthogonal matching pursuit section of the pipeline as an alternate method to determine location of
    spots and their gene identity.
    It achieves this by fitting multiple gene bled codes to each pixel to find a coefficient for every gene at
    every pixel. Spots are then local maxima in these gene coefficient images.

    `omp` page is added to the Notebook before saving.

    Args:
        - (Notebook) nb: `Notebook` containing `call_spots` page.
        - (NotebookPage) nbp_file: `file_names` notebook page.
    """
    if not nb.has_page("omp"):
        config = setup.config.get_config(nb.config_path)
        # Use tile with most spots on to find spot shape in omp
        nbp = omp_torch.run_omp(
            config["omp"],
            nbp_file,
            nb.basic_info,
            nb.extract,
            nb.filter,
            nb.register,
            nb.stitch,
            nb.call_spots,
        )
        nb += nbp
    else:
        log.warn(utils_warnings.NotebookPageWarning("omp"))
