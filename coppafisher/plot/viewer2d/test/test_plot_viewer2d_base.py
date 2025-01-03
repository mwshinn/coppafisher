import os

from coppafisher import Viewer2D


def Viewer2D_test() -> None:
    #! Requires robominnie to have successfully run through at least up to call spots.
    print(os.path.dirname(os.path.realpath(__file__)))
    notebook_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))),
        "robominnie",
        "test",
        ".integration_dir",
        "output_coppafisher",
        "notebook.npz",
    )
    gene_colours_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))),
        "robominnie",
        "test",
        ".integration_dir",
        "gene_colours.csv",
    )
    assert os.path.isfile(notebook_path), "Failed to find notebook at\n" + notebook_path
    assert os.path.isfile(gene_colours_path), "Failed to find gene markers at\n" + gene_colours_path
    # Viewer2D(notebook_path, gene_marker_file=gene_colours_path)
    Viewer2D(r"C:\Users\Paul\Downloads\notebook.npz")
