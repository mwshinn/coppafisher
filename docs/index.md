## Coppafish

<div class="grid cards no-format" markdown>

 - [:material-checkbox-multiple-blank: __Zarr__ for image compression](https://zarr.readthedocs.io/)
 - [:material-fast-forward:  __PyTorch__ for GPU/CPU acceleration](https://pytorch.org/)
 - [:material-eye:  __Napari__ for 3D visualisation](https://napari.org/)
 - [:material-web:  __Dash__ for web interaction](https://dash.plotly.com/)

</div>

Coppafish is an open source data analysis software for COmbinatorial Padlock-Probe-Amplified Fluorescence In Situ
Hybridization (coppafish) datasets. A series of 3D microscope images are arranged into tiles, rounds and channels. For
each sequencing round, every considered gene is fluoresced by a dye. By the end of all rounds, each gene has a unique,
barcode-like sequence of dyes called the gene code. Coppafish is a data analysis pipeline to decode gene's by their 
gene codes in 3D.

For more details about coppafish's methodology, see the
[overview](overview.md). See [installation](#installation) on how to install our software, and [usage](basic_usage.md) to
run coppafish on your dataset. Some vocabulary might be unfamiliar, please see the [glossary](glossary.md) for
reference.

<figure markdown="span">
  ![Image title](images/coppafish_simple_schematic.png){ width="400" }
  <figcaption>Gene calling on a tile.</figcaption>
</figure>

## Installation

### Prerequisites

* Windows or Linux. MacOS is not tested.
* Python 3.10 or 3.11.
* [Git](https://git-scm.com/).
* 64GB of memory for tile sizes `64x2048x2048` pixels (recommended).
* Nvidia GPU with Cuda 12.4 support (optional).

### Environment

Install coppafish software from within an environment. We will use a conda environment, so 
[miniconda](https://docs.anaconda.com/miniconda/) or [anaconda](https://anaconda.org/anaconda/conda) is required.

First, build an environment

```terminal
conda create -n coppafish python=3.11
conda activate coppafish
```

### Install

Clone the latest coppafish release locally 

```terminal
git clone --depth 1 https://github.com/paulshuker/coppafish
```

or get a specific version. For example, version 1.0.0 

```terminal
git clone --depth 1 --branch 1.0.0 https://github.com/paulshuker/coppafish
```

install package dependencies by

```terminal
cd coppafish
python -m pip install -r requirements.txt
```

install [PyTorch](https://pytorch.org/) with both CPU and Cuda 12.4 support by 

```terminal
python -m pip install -r requirements-torch.txt
```

You can check that a GPU is detected and working in the python terminal

```py
import torch
torch.cuda.is_available()
```

which should give true. Finally, install coppafish by 

```terminal
python -m pip install .
```

You can now safely delete the locally cloned coppafish repository.

## Updating

Coppafish will not automatically install updates. But, you will see a warning at the start of a pipeline if a new 
online version is available.

To update version, delete the old conda environment by `#!terminal conda env remove -n coppafish`. Then follow all 
[installation](#installation) instructions again.

You can verify your install by running `#!terminal pip show coppafish` in the coppafish environment to check you have the 
latest version.

Keep all output data (including the notebook) when updating coppafish versions. If data saved to disk is now 
deprecated, coppafish will automatically suggest a course of action when it is [run](basic_usage.md#running).
