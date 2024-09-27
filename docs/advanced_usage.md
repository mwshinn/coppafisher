## Change configuration

Each coppafish section is saved as separate notebook page(s). To change the config variables and re-run the coppafish 
pipeline, you can delete the notebook and all output directory files and re-run again. But, if you only wished to 
re-run starting from an intermediate stage, you can delete all subsequent stages and output files. To see what valid 
stages of coppafish you can re-run starting from, in chronological order, in the python terminal

```python
from coppafish.utils import CompatibilityTracker

tracker = CompatibilityTracker()
tracker.print_stage_names()
```

As an example, if you wished to know how to start from the stage "find_spots" again

```python
from coppafish.utils import CompatibilityTracker

tracker = CompatibilityTracker()
tracker.print_start_from("find_spots")
```

and follow the instructions given. Then, you are safe to change the configuration for all sections after find spots. If 
you are told to delete notebook page(s), see [here](#delete-notebook-page).

## Skipping bad microscope images

You may have one or more images that are taken which are corrupted, empty, or not as bright as expected. When this
happens, the user can manually tell coppafish to run without these images. To do this, specify each tile (`t`), round
(`r`), channel (`c`) image by going to your custom config file and add the line

```
bad_trc = (t1, r1, c1), (t2, r2, c2), ...
```

under the `basic_info` section. Each set of brackets represents one image to ignore. This allows for meaningful 
results to be salvaged from a tile.

## Exporting results for pciSeq

For probabilistic cell typing with [pciSeq](https://github.com/acycliq/pciSeq), you can export gene reads into a 
compatible csv file by 

```python
from coppafish import Notebook
from coppafish.utils import export_to_pciseq

nb = Notebook("/path/to/notebook")
export_to_pciseq(nb, method)
```

where method can be "omp", "prob", or "anchor" for each gene calling method. To set a score and/or intensity minimum 
threshold, 

```python
export_to_pciseq(nb, method, score_thresh, intensity_thresh)
```

where score_thresh and intensity_thresh are numbers. Check the [Viewer](dianogstics.md#Viewer) for help deciding on 
thresholds.

## Create a background process

Large datasets can have a long compute time (in the order of days). It is recommended to run these by setting them up 
as a background process. It is not recommended to run multiple large datasets at once since they will be fighting for 
memory, CPU, and disk I/O resources. Running in the background depends on the operating system:

### Linux

Start a background process from a terminal with the coppafish conda environment activated

```bash
nohup python3 -m coppafish /path/to/config.ini &
```

the background process will run, even if the terminal is now closed. Follow its progress by

```bash
tail -f nohup.out
```

press Ctrl + C to stop following. The process can be killed by finding it after running a command like `htop`, 
highlighting it, press F9, then Enter to kill it. Press q to exit the `htop` view.

### Windows

Open a command prompt, run the command

```terminal
start /b python -m C:\path\to\config.ini
```

Try to keep the command prompt open to watch the progress. Do not log out or shutdown the PC while the process is still 
running.

## Delete notebook page

To remove a notebook page, in the python terminal

```python
from coppafish import Notebook

nb = Notebook("/path/to/notebook")
nb.delete_page("page_name")
```

For example, to remove the omp page

```python
from coppafish import Notebook

nb = Notebook("/path/to/notebook")
nb.delete_page("omp")
```

## Email notification

To be emailed when the pipeline crashes or finishes, under section `[notifications]` in the config, add the variable 
`email_me` with your email address. You must have a sender email with SMTP support, this email's credentials must be 
given in `[notifications]` under the variables `sender_email` and `sender_email_password`. The email may be flagged as 
junk or not be sent altogether, depending on the email address to be sent to. This has only been tested for an 
"outlook.com" Microsoft email.

## Generate gene codes

Generate gene codes automatically in the python terminal by

```python
from coppafish.utils import reed_solomon_codes

codes = reed_solomon_codes(n_gene_codes, n_rounds, n_channels)
```

where `n_gene_codes` is the number of gene codes desired, `n_rounds` is the number of sequencing rounds, and 
`n_channels` is the number of channels. An error is thrown if the number of unique gene codes desired is impossible to 
create. Each channel is labelled 0, 1, 2, ... and `codes` is a dictionary. Each gene code generated can be accessed. 
For example, to access the first gene code: `codes["gene_0"]`.

## Retrieve the Notebook config

Every notebook page has associated config section(s) saved to disk. You can look at each notebook page's associated 
config section(s). For example, to see the associated config section(s) for the filter page, in the python terminal

```python
from coppafish import Notebook

nb = Notebook("path/to/notebook")
nb.filter.associated_configs  # Dictionary of associated config sections.
```
