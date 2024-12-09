import json
import numbers
import os
from typing import List, Optional, Tuple, Union

import nd2
import numpy as np
import numpy_indexed
from tqdm import tqdm

from .. import log, setup
from ..setup import tile_details
from . import raw

# bioformats ssl certificate error solution:
# https://stackoverflow.com/questions/35569042/ssl-certificate-verify-failed-with-python3


class NoFileError(Exception):
    def __init__(self, file_path: str):
        """
        Error raised because `file_path` does not exist.

        Args:
            file_path: Path to file of interest.
        """
        self.message = f"\nNo file with the following path:\n{file_path}\nexists"
        super().__init__(self.message)


# nd2 library Does not work with Mac M1
def load(file_path: str) -> Tuple[np.ndarray, dict]:
    """
    Get ND2 as a dask array with indices in order `fov`, `channel`, `y`, `x`, `z`.

    Args:
        file_path: Path to desired nd2 file.

    Returns:
        Dask array indices in order `fov`, `channel`, `y`, `x`, `z`.
    """
    if not os.path.isfile(file_path):
        raise NoFileError(file_path)
    with nd2.ND2File(file_path) as images:
        images = images.to_dask()
    # images = nd2.imread(file_name, dask=True)  # get python crashing with this in get_image for some reason
    images = np.moveaxis(images, 1, -1)  # put z index to end
    return images


def get_raw_extension(input_dir: str) -> str:
    """
    Looks at input directory and returns the raw data format
    Args:
        input_dir: input_directory from config file containing raw data
    Returns:
        raw_extension: str, either 'nd2', 'npy' or 'jobs'
    """
    # Want to list all files in input directory and all subdirectories. We'll use os.walk
    files = []
    for root, directories, filenames in os.walk(input_dir):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    files.sort()
    # Just need a single npy to confirm this is the format
    if any([directory.endswith("npy") for directory in files]):
        raw_extension = ".npy"
    else:
        # Get the first nd2 file here
        index = min([i for i in range(len(files)) if files[i].endswith("nd2")])

        with nd2.ND2File(os.path.join(input_dir, files[index])) as image:
            if image.sizes["C"] == 28:
                raw_extension = ".nd2"
            else:
                raw_extension = "jobs"
    return raw_extension


def get_metadata(file_path: str, config: dict) -> dict:
    """
    Gets metadata containing information from nd2 data about pixel sizes, position of tiles and numbers of
    tiles/channels/z-planes.

    Args:
        file_path: path to desired nd2 file
        config: config dictionary

    Returns:
        Dictionary containing - n_tiles, n_channels, tile_sz, pixel_size_xy, pixel_size_z, tile_centre, xy_pos, nz,
        tilepos_yx_nd2, tilepos_yx, channel_laser, channel_camera, n_rounds

    """

    if not os.path.isfile(file_path):
        raise NoFileError(file_path)

    with nd2.ND2File(file_path) as images:
        metadata = {
            "n_tiles": images.sizes["P"],
            "n_channels": images.sizes["C"],
            "tile_sz": images.sizes["X"],
            "pixel_size_xy": images.metadata.channels[0].volume.axesCalibration[0],
            "pixel_size_z": images.metadata.channels[0].volume.axesCalibration[2],
        }
        # Check if data is 3d
        if "Z" in images.sizes:
            # subtract 1 as we always ignore first z plane
            nz = images.sizes["Z"]
            metadata["tile_centre"] = np.array([metadata["tile_sz"], metadata["tile_sz"], nz]) / 2
        else:
            metadata["tile_centre"] = np.array([metadata["tile_sz"], metadata["tile_sz"]]) / 2

        xy_pos = np.array(
            [images.experiment[0].parameters.points[i].stagePositionUm[:2] for i in range(images.sizes["P"])]
        )
        xy_pos = (xy_pos - np.min(xy_pos, 0)) / metadata["pixel_size_xy"]
        metadata["xy_pos"] = xy_pos
        metadata["tilepos_yx_nd2"], metadata["tilepos_yx"] = tile_details.get_tilepos(
            xy_pos=xy_pos, tile_sz=metadata["tile_sz"], expected_overlap=config["stitch"]["expected_overlap"]
        )
        # Now also extract the laser and camera associated with each channel
        desc = images.text_info["description"]
        channel_metadata = desc.split("Plane #")[1:]
        laser = np.zeros(len(channel_metadata), dtype=int)
        camera = np.zeros(len(channel_metadata), dtype=int)
        for i in range(len(channel_metadata)):
            laser[i] = int(
                channel_metadata[i][channel_metadata[i].index("; On") - 3 : channel_metadata[i].index("; On")]
            )
            camera[i] = int(
                channel_metadata[i][channel_metadata[i].index("Name:") + 6 : channel_metadata[i].index("Name:") + 9]
            )
        metadata["channel_laser"] = laser.tolist()
        metadata["channel_camera"] = camera.tolist()
        # Get the entire input directory to list
        metadata["n_rounds"] = len(config["file_names"]["round"])
        metadata["nz"] = nz

    return metadata


def get_all_metadata(file_path: str) -> dict:
    """
    Gets all found metadata from nd2 file.

    Args:
        file_path (str): path to desired nd2 file.

    Returns:
        dict: dictionary containing all found metadata for given ND2 file.
    """
    if not os.path.isfile(file_path):
        raise NoFileError(file_path)

    with nd2.ND2File(file_path) as images:
        metadata = images.unstructured_metadata()
    return dict(metadata)


def get_jobs_metadata(files: list, input_dir: str, config: dict) -> dict:
    """
    Gets metadata containing information from nd2 data about pixel sizes, position of tiles and numbers of
    tiles/channels/z-planes. This has to be as separate function from above due to the fact that input here is a list
    of directories as rounds are not entirely contained in a single file for jobs data.

    Args:
        files: list of paths to desired nd2 file
        input_dir: Directory to location of files
        config: config dictionary
    Returns:
        Dictionary containing -

        - `xy_pos` - `List [n_tiles x 2]`. xy position of tiles in pixels.
        - `pixel_microns` - `float`. xy pixel size in microns.
        - `pixel_microns_z` - `float`. z pixel size in microns.
        - `sizes` - dict with fov (`t`), channels (`c`), y, x, z-planes (`z`) dimensions.
        - 'channels' - list of colorRGB codes for the channels, this is a unique identifier for each channel
    """
    # Get simple metadata which is constant across tiles from first file
    with nd2.ND2File(os.path.join(input_dir, files[0])) as im:
        metadata = {
            "tile_sz": im.sizes["X"],
            "pixel_size_xy": im.metadata.channels[0].volume.axesCalibration[0],
            "pixel_size_z": im.metadata.channels[0].volume.axesCalibration[2],
        }
        # Check if data is 3d
        if "Z" in im.sizes:
            # subtract 1 as we always ignore first z plane
            nz = im.sizes["Z"]
            metadata["tile_centre"] = np.array([metadata["tile_sz"], metadata["tile_sz"], nz]) / 2
        else:
            # Our microscope setup is always square tiles
            metadata["tile_centre"] = np.array([metadata["tile_sz"], metadata["tile_sz"]]) / 2

    # Now loop through the files to get the more varied data
    xy_pos = []
    laser = []
    camera = []

    # Only want to extract metadata from round 0
    for f_id, f in tqdm(enumerate(files), desc="Reading metadata from all files"):
        with nd2.ND2File(os.path.join(input_dir, f)) as im:
            stage_position = [int(x) for x in im.frame_metadata(0).channels[0].position.stagePositionUm[:2]]
            # We want to append if this stage position is new
            # We also want to break if we have reached the end of the tiles. We expect xy_pos to be the same value for
            # file 0, ..., n_lasers - 1, then the next value for file n_lasers, ..., 2*n_lasers - 1, etc. But when we
            # reach the end of the tiles, we will eventually loop back to tile 0, so we want to break when we reach.
            if stage_position not in xy_pos:
                xy_pos.append(stage_position)
            all_tiles_complete = (stage_position in xy_pos) * (stage_position != xy_pos[-1])
            if all_tiles_complete:
                break
            cal = im.metadata.channels[0].volume.axesCalibration[0]
            # Now also extract the laser and camera associated with each channel
            desc = im.text_info["description"]
            channel_metadata = desc.split("Plane #")[1:]
            # Since channels constant across tiles only need to gauge from tile 1
            if stage_position == xy_pos[0]:
                for i in range(len(channel_metadata)):
                    laser_wavelength = int(
                        channel_metadata[i][channel_metadata[i].index("; On") - 3 : channel_metadata[i].index("; On")]
                    )
                    camera_wavelength = int(
                        channel_metadata[i][
                            channel_metadata[i].index("Name:") + 6 : channel_metadata[i].index("Name:") + 9
                        ]
                    )
                    laser.append(laser_wavelength)
                    camera.append(camera_wavelength)

    # Normalise so that minimum is 0,0
    xy_pos = np.array(xy_pos)
    xy_pos = (xy_pos - np.min(xy_pos, axis=0)) / cal
    metadata["xy_pos"] = xy_pos
    metadata["tilepos_yx_nd2"], metadata["tilepos_yx"] = setup.get_tilepos(
        xy_pos=xy_pos, tile_sz=metadata["tile_sz"], expected_overlap=config["stitch"]["expected_overlap"]
    )
    metadata["n_tiles"] = len(metadata["tilepos_yx_nd2"])
    # get n_channels and channel info
    metadata["channel_laser"], metadata["channel_camera"] = laser, camera
    metadata["n_channels"] = len(laser)
    # Final piece of metadata is n_rounds. Note num_files = num_rounds * num_tiles * num_lasers
    n_files = len(os.listdir(input_dir))
    n_lasers = len(set(laser))

    metadata["n_rounds"] = n_files // (n_lasers * metadata["n_tiles"])
    # TODO find a better solution to fix the number of rounds
    metadata["n_rounds"] -= 1
    metadata["nz"] = nz

    return metadata


def get_images(images: np.ndarray, fov: int, channels: List[int], use_z: Optional[List[int]] = None) -> np.ndarray:
    """
    Using dask array from nd2 file, this loads the image of the desired fov and channel.

    Args:
        images: Dask array with `fov`, `channel`, y, x, z as index order.
        fov: `fov` index of desired image
        channel: `channel` of desired image
        use_z: `int [n_use_z]`.
            Which z-planes of image to load.
            If `None`, will load all z-planes.

    Returns:
        `uint16 [im_sz_y x im_sz_x x n_use_z]`.
            Image of the desired `fov` and `channel`.
    """
    assert isinstance(channels, list)
    if use_z is None:
        use_z = np.arange(images.shape[-1])
    all_channels = np.asarray(images[fov, :, :, :, use_z])
    return tuple([all_channels[c].copy() for c in channels])


def save_metadata(json_file: str, nd2_file: str, use_channels: Optional[List] = None):
    """
    Saves the required metadata as a json file which will contain

    - `xy_pos` - `List [n_tiles x 2]`. xy position of tiles in pixels.
    - `pixel_microns` - `float`. xy pixel size in microns.
    - `pixel_microns_z` - `float`. z pixel size in microns.
    - `sizes` - dict with fov (`t`), channels (`c`), y, x, z-planes (`z`) dimensions.

    Args:
        json_file: Where to save json file
        nd2_file: Path to nd2 file
        use_channels: The channels which have been extracted from the nd2 file.
            If `None`, assume all channels in nd2 file used

    """
    metadata = get_metadata(nd2_file)
    if use_channels is not None:
        if len(use_channels) > metadata["sizes"]["c"]:
            log.error(
                ValueError(
                    f"use_channels contains {len(use_channels)} channels but there "
                    f"are only {metadata['sizes']['c']} channels in the nd2 metadata."
                )
            )
        metadata["sizes"]["c"] = len(use_channels)
        metadata["use_channels"] = use_channels  # channels extracted from nd2 file
    json.dump(metadata, open(json_file, "w"))


def get_nd2_tile_ind(
    tile_ind_npy: Union[int, List[int]], tile_pos_yx_nd2: np.ndarray, tile_pos_yx_npy: np.ndarray
) -> Union[int, List[int]]:
    """
    Gets index of tiles in nd2 file from tile index of npy file.

    Args:
        tile_ind_npy: Indices of tiles in npy file.
        tile_pos_yx_nd2: ``int [n_tiles x 2]``.
            ``[i,:]`` contains YX position of tile with nd2 index ``i``.
            Index 0 refers to ``YX = [0, 0]``.
            Index 1 refers to ``YX = [0, 1] if MaxX > 0``.
        tile_pos_yx_npy: ``int [n_tiles x 2]``.
            ``[i,:]`` contains YX position of tile with npy index ``i``.
            Index 0 refers to ``YX = [MaxY, MaxX]``.
            Index 1 refers to ``YX = [MaxY, MaxX - 1] if MaxX > 0``.

    Returns:
        Corresponding indices in nd2 file.
    """
    if isinstance(tile_ind_npy, numbers.Number):
        tile_ind_npy = [tile_ind_npy]
    # As npy and nd2 have different coordinate systems, we need to convert tile_pos_yx_npy to nd2 tile coordinates
    tile_pos_yx_npy = np.max(tile_pos_yx_npy, axis=0) - tile_pos_yx_npy
    # TODO: Remove the obscure dependency for a line.
    nd2_index = numpy_indexed.indices(tile_pos_yx_nd2, tile_pos_yx_npy[tile_ind_npy]).tolist()
    if len(nd2_index) == 1:
        return nd2_index[0]
    else:
        return nd2_index
    # return np.where(np.sum(tile_pos_yx_nd2 == tile_pos_yx_npy[tile_ind_npy], 1) == 2)[0][0]


def get_raw_images(
    nbp_basic,
    nbp_file,
    tiles: List[int],
    rounds: List[int],
    channels: List[int],
    use_z: List[int],
) -> np.ndarray:
    """
    This loads in raw images for the experiment corresponding to the *Notebook*.

    Args:
        nbp_basic: basic info page of relevant notebook (NotebookPage)
        nbp_file: File names info page of relevant notebook (NotebookPage)
        tiles: npy (as opposed to nd2 fov) tile indices to view.
            For an experiment where the tiles are arranged in a 4 x 3 (ny x nx) grid, tile indices are indicated as
            below:

            | 2  | 1  | 0  |

            | 5  | 4  | 3  |

            | 8  | 7  | 6  |

            | 11 | 10 | 9  |
        rounds: Rounds to view.
        channels: Channels to view.
        use_z: Which z-planes to load in from raw data.

    Returns:
        `raw_images` - `[len(tiles) x len(rounds) x len(channels) x n_y x n_x x len(use_z)]` uint16 array.
        `raw_images[t, r, c]` is the `[n_y x n_x x len(use_z)]` image for tile `tiles[t]`, round `rounds[r]` and channel
        `channels[c]`.
    """
    n_tiles = len(tiles)
    n_rounds = len(rounds)
    n_channels = len(channels)
    n_images = n_rounds * n_tiles * n_channels
    ny = nbp_basic.tile_sz
    nx = ny
    nz = len(use_z)

    raw_images = np.zeros((n_tiles, n_rounds, n_channels, ny, nx, nz), dtype=np.uint16)
    with tqdm(total=n_images) as pbar:
        pbar.set_description("Loading in raw data")
        for r in range(n_rounds):
            round_dask_array, _ = raw.load_dask(nbp_file, nbp_basic, r=rounds[r])
            # TODO: Can get rid of these two for loops, when round_dask_array is always a dask array.
            #  At the moment though, is not dask array when using nd2_reader (On Mac M1).
            for t in range(n_tiles):
                for c in range(n_channels):
                    pbar.set_postfix({"round": rounds[r], "tile": tiles[t], "channel": channels[c]})
                    (raw_images[t, r, c],) = raw.load_image(
                        nbp_file, nbp_basic, tiles[t], channels[c], round_dask_array, rounds[r], use_z
                    )
                    pbar.update(1)
    return raw_images


def get_bleed_estimates(dye_image: list, dye_names: list, percentiles: list = [80, 90]) -> dict:
    """
    Estimate bleed matrix from dye images. Do this by taking in a list of images (one for each dye) and then
    looking for the top ~ 10% of non-saturated pixels in each image. This gives us many data points to average over,
    thereby reducing the effect of noise.
    Args:
        dye_image: list (n_dyes) of dye images (n_channels x n_pixels)
        dye_names: list (n_dyes) of dye names
        percentiles: list (2) of percentiles to use to get the top ~ 10% of pixels
    Returns:
        bleed: dict (n_dyes) of bleed estimates (n_channels)
    """
    n_dyes = len(dye_image)
    n_channels = dye_image[0].shape[0]
    dye_image = np.array(dye_image)
    dye_image = dye_image.reshape((n_dyes, n_channels, -1))
    bleed = {}
    for d in range(n_dyes):
        # allow for 1 saturated channel as this is likely to be the case for a channel we are not using
        saturated_channels = np.sum(dye_image[d] == 65_535, axis=0)
        use = saturated_channels <= 1
        d_pixels = dye_image[d][:, use]
        # get approx top 10% of non-saturated pixels as measured by the mean across channels
        intensity = np.mean(d_pixels, axis=0)
        intensity_threshold_low, intensity_threshold_high = np.percentile(intensity, percentiles)
        bright = (intensity > intensity_threshold_low) * (intensity < intensity_threshold_high)
        # get bleed estimates by averaging across pixels
        bleed[dye_names[d]] = np.mean(d_pixels[:, bright], axis=1)

    return bleed
