* Anchor round - A single round taken, usually on a chosen "anchor channel" that has a high Signal-to-Noise Ratio
(SNR). All genes of interest are given the same fluorescing dye probe so that every spot lights up. The anchor round is
essential for detecting all spots at once in the same microscope image.

* Background gene - Background genes refer to constant pixel intensity across all sequencing rounds in one channel. This
is an indicator of an anomalous fluorescing artefact that is not a spot. No spot codes are made to be the same channel
in all rounds. This way spots are not mistaken for background fluorescence and vice versa.

* Bled code - Every gene has a unique bled code. It is a series of intensities expected in each sequencing
round/channel. Its bled code is dependent on the gene's gene code and the bleed matrix.

* Bleed matrix - How intense each dye is in each sequencing channel. This is estimated during the
[call spots](overview.md#call-spots) stage.

* Channel - A combination of excitation light of a certain wavelength and specific emission filter. We use multiple
channels to distinguish every dye colour (almost always the number of channels is equal to the number of unique dyes).
But, a dye can have "bleed through", i.e. brightness in multiple channels from the same dye.

* DAPI - A dye that fluoresces the nuclei of all cells. It is used to [register](overview.md#register) between
sequencing rounds. The DAPI is also a background image in the [Viewer](diagnostics.md#viewer).

* Gene code - A sequence of dyes that are assigned to a gene for each sequencing round. Each gene has a unique gene
code. For example, if the dyes are labelled `0, 1, 2` and there are 2 sequencing rounds, some example gene codes are
`0, 1` (i.e. dye `0` in first round, dye `1` in second round), `1, 2`, `0, 2`.

* Notebook - A write-once[^1] compressed file that stores all important outputs from coppafisher. The notebook is used
to plot many [diagnostics](diagnostics.md). The notebook contains notebook pages. There is at least one notebook page
for each [method](overview.md) section. A notebook can be loaded by
`#!python from coppafisher import Notebook; nb = Notebook("path/to/notebook")`. Variables from the notebook can be
directly read. For example, you can read the `use_tiles` variable from the `basic_info` page by
`#!python print(nb.basic_info.use_tiles)`. Each variable has a description, which can be printed. For example,
`#!python nb.basic_info > "use_tiles"`.

* OMP - Stands for [Orthogonal Matching Pursuit](overview.md#orthogonal-matching-pursuit). It is the final section of
the coppafisher pipeline. It is coppafisher's most sophisticated algorithm for gene calling and is used as a way of
untangling genes that overlap by assuming that the pixel intensity is a linear combination of each gene bled code. There
is currently no reason to suspect that gene bled codes combine non-linearly.

* Point cloud - A series of spatial pixel positions. Typically used to represent detected spot positions during
[find spots](overview.md#find-spots).

* PSF - Stands for Point Spread Function and is used during image filtering. The Wiener deconvolution requires a PSF to
remove blurring caused by frequencies with a low signal-to-noise ratio. See the [filter](overview.md#filter) overview
and the <a href="https://en.wikipedia.org/wiki/Wiener_deconvolution" target="_blank">Wikipedia article</a> for more
details.

* Sequencing round - An image of the tissue, made up of multiple tiles and sequencing channels. Before each imaging
round, the tissue is treated with various solutions to remove the previous DNA probes and then hybridise new ones. Each
spot will bind to a specific bridge probe which then binds to a fluorescing dye probe, causing it to fluoresce in
specific channel(s). The colour of each spot in each round is dictated by its gene identity (identities) and their
corresponding gene code(s).

* Spot - An amplified ball of DNA with a unique barcode specific to each gene. The gene can be determined by looking at
the same spot in all sequencing rounds to reveal the gene code. Coppafisher takes the raw images of the spots as input
and outputs the gene identity of each spot in situ.

* Tile - A cuboid subset of the microscope image of pixel size $n_z \times n_y \times n_x$ in z, y, and x, where
$n_y = n_x \sim 2000 \text{ pixels}$. Typically, $n_z\sim10\text{s}$. Usually, all adjacent tiles overlap by
$10\%-15\%$ to give coppafisher sufficient information to align tiles (see [stitch](overview.md#stitch) for details).


[^1]:
    There are some cases of notebooks being "rewritten", see [advanced usage](advanced_usage.md).
