from coppafish import Notebook
from coppafish.pciseq import export_to_pciseq

nb = Notebook("/path/to/notebook")
export_to_pciseq(nb, method, score_thresh, intensity_thresh)
