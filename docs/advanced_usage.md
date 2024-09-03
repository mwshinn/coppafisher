## Running in the background

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

and press Ctrl + C to stop following. The process can be killed by finding it after running a command like `htop`, 
highlighting it, pres F9, then Enter to kill it. Press q to exit the `htop` view.

### Windows

Open a command prompt, run the command

```terminal
start /b python -m C:\path\to\config.ini
```

Try to keep the command prompt open to watch the progress. Do not log out or shutdown the PC while the process is 
still running.

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

## Removing notebook pages

Each coppafish section is saved as a separate notebook page. To change the config variables and re-run the coppafish 
pipeline, you can delete the notebook and all output directory files and re-run again. But, if you only wished to 
re-run starting from an intermediate stage, you can delete all subsequent stages and output files. To see what 
valid stages of coppafish you can re-run starting from, run in the python terminal

```python
from coppafish import CompatibilityTracker
tracker = CompatibilityTracker()
tracker.print_stage_names()
```

As an example, if you wished to know how to start from the stage "find_spots" again

```python
from coppafish import CompatibilityTracker
tracker = CompatibilityTracker()
tracker.print_start_from("find_spots")
```

and follow the instructions given.

## Skipping bad microscope images

You may have one or more images that are taken which are corrupted, empty, or not as bright as expected. When this
happens, the user can manually tell coppafish to run without these images. To do this, specify each tile (`t`), round
(`r`), channel (`c`) image by going to your custom config file and add the line

```
bad_trc = (t1, r1, c1), (t2, r2, c2), ...
```

under the `basic_info` section. Each set of brackets represents one image to ignore. This allows for meaningful 
results to be salvaged from a tile.

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

The notebook stores a path to the associated config file, this can be accessed by doing

```python
from coppafish import Notebook

nb = Notebook("path/to/notebook")
config = nb.config_path
```

Every notebook page has its associated config section(s) stored within the notebook as well. This is used internally 
to check for unexpected configuration changes compared to the config file kept separately on disk to warn the user. 
You can look at each notebook page's associated config section(s). For example, to see the associated config 
section(s) for filter, in the python terminal

```python
from coppafish import Notebook

nb = Notebook("path/to/notebook")
nb.filter.associated_configs  # Dictionary of associated config sections.
```

