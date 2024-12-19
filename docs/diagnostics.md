Diagnostics specific to a method are found in the [method](find_spots.md) tab.

## Viewer

The Viewer is the flagship diagnostic for viewing results. It is a fast, three-dimensional view of gene reads found
during [call spots](overview.md#call-spots) and [OMP](overview.md#orthogonal-matching-pursuit). The application is
powered by [napari](https://github.com/napari/napari).

### Opening

A Viewer can be displayed once coppafish has run through at least [call spots](overview.md#call-spots). From the python
terminal:

```py
from coppafish import Notebook, Viewer

nb = Notebook("/path/to/notebook")
Viewer(nb)
```

or from the command line

```terminal
python -m coppafish -v /path/to/notebook
```

where a napari window will be opened.

You can specify the colour and symbols of genes using a .csv file, then the Viewer can be opened by

```py
from coppafish import Notebook, Viewer

nb = Notebook("/path/to/notebook")
Viewer(nb, gene_marker_file="/path/to/custom/gene_marker_file.csv")
```

or by the terminal

```terminal
python -m coppafish -v /path/to/notebook --gene_marker /path/to/gene_marker.csv
```

see [here](https://github.com/paulshuker/coppafish/raw/HEAD/coppafish/plot/results_viewer/gene_colour.csv) for the
default gene marker file.

You can specify a custom background image in the python terminal. The default is a dapi image over all tiles produced
during stitch.

```py
from coppafish import Notebook, Viewer

nb = Notebook("/path/to/notebook")
Viewer(nb, background_image="/path/to/custom/background_image.npy")
```

The background image must be of shape `(im_y x im_x)` or `(im_z x im_y x im_x)` and can be a .npy file, a compressed
.npz file with image at key `"arr_0"`, or a .tif file (based on package
[tifffile](https://github.com/cgohlke/tifffile)). For further customisation, see the Viewer
[docstring](https://github.com/paulshuker/coppafish/blob/HEAD/coppafish/plot/results_viewer/base.py).

Close the Viewer and all subplots by pressing Ctrl + C in the terminal.

### Description

The greyscale signal in the background is the DAPI by default, where whiter regions indicate cells. Each gene is given
a unique shape and colour, shown in the gene legend. A gene can be toggled by left clicking on it in the gene legend,
right click a gene to show only that type. Right click it again to show all genes again.

For help with Viewer hotkeys, press h. This includes further diagnostic subplots in the Viewer. Some require a selected
spot. Select a spot by pressing 3 and clicking on a spot. Press 4 to continue panning.

The "Background Contrast" slider will affect the colour scale of the background image. "Marker Size" will change the
size of gene spots. "Z Thickness" allows for multiple z planes to be displayed at once. The "Score Thresholds" allows
the user to change the minimum and maximum spot scores to display. The "Intensity Thresholds" affects the minimum and
maximum allowed spot intensity to display The "Method" is the chosen method of gene calling. "Probability" is the Von-
Mises probability method, "Anchor" is the anchor method (see [call spots](overview.md#call-spots)), and "OMP" is the
Orthogonal Matching Pursuit method (see [OMP](overview.md#orthogonal-matching-pursuit)).

<figure markdown="span">
  ![Image title](images/Viewer_example.PNG){ width="1100" }
  <figcaption>The Viewer</figcaption>
</figure>

## RegistrationViewer

### Opening

```python
from coppafish import RegistrationViewer, Notebook

nb = Notebook("/path/to/notebook")
RegistrationViewer(nb, "/path/to/config.ini" t=t)
```

where `t` is a tile index you want to view registration results for. If `t` is set to `None` (default), then the lowest
tile index is displayed.

## PDF Diagnostics

During a pipeline run, multiple .pdf files are created for different sections. These are located in the output
directory. If you want the PDFs to be created again, delete the old ones first, then
[run coppafish](basic_usage.md/#running) again.

## Viewer2D

To open
```python
from coppafish import Notebook, Viewer2D

nb = Notebook("/path/to/notebook")
Viewer2D(nb)
```

The viewer is updated by typing commands in the terminal. To find out the available commands, type `help` or `h`.

## Viewing images

### Extracted images

Extracted images are identical to raw images, these are viewed by

```python
from coppafish import Notebook, plot

nb = Notebook("/path/to/notebook")
plot.view_extracted_images(nb, "/path/to/config.ini", tiles, rounds, channels)
```

where `tiles`, `rounds`, and `channels` are lists of integers specifying which images to view. Set these to `None` if
you wish to view all of the them from the sequencing images.

### Filtered images

Images after the [filter](overview.md#filter) stage are viewed by

```python
from coppafish import Notebook, plot

nb = Notebook("/path/to/notebook")
plot.view_filtered_images(nb, tiles, rounds, channels, apply_colour_norm_factor=True, share_contrast_limits=True)
```

where `tiles`, `rounds`, and `channels` are lists of integers specifying which images to view. Set these to `None` if
you wish to view all of the them from the sequencing images. The boolean parameters can be set to `False` if needed.

### Intensity images

You can view the computed intensities once call spots is complete. Do this by

```py
from coppafish import Notebook, plot

nb = Notebook("/path/to/notebook")
plot.view_intensity_images(nb, tiles)
```

`tiles` is a list of integers for each tile index to view. If set to `None`, the first tile is shown.
