import matplotlib.pyplot as plt


class Hotkeys:
    key_to_str = lambda key: key.lower().replace("-", " + ")
    view_hotkeys = "Shift-k"
    switch_zoom_select = "Space"
    remove_background = "i"
    view_bleed_matrix = "b"
    view_background_norm = "n"
    view_bleed_matrix_calculation = "Shift-b"
    view_bled_codes = "g"
    view_all_gene_scores = "Shift-h"
    view_gene_efficiency = "e"
    # view_gene_counts = "Shift-g"
    view_histogram_scores = "h"
    view_scaled_k_means = "k"
    view_colour_and_codes = "c"
    view_spot_intensities = "s"
    view_spot_colours_and_weights = "d"
    view_intensity_from_colour = "Shift-i"
    view_omp_coef_image = "o"
    # view_omp_pixel_colours = "p"


class ViewHotkeys:
    def __init__(self) -> None:
        fig, ax = plt.subplots(1, 1)
        fig.tight_layout()
        fig.suptitle("Hotkeys", size=20)
        ax.set_axis_off()
        text = f"""Toggle between zoom and spot selection: {Hotkeys.key_to_str(Hotkeys.switch_zoom_select)}
                Remove background image: {Hotkeys.key_to_str(Hotkeys.remove_background)}
                View bleed matrix: {Hotkeys.key_to_str(Hotkeys.view_bleed_matrix)}
                View background, normalised: {Hotkeys.key_to_str(Hotkeys.view_background_norm)}
                View bleed matrix calculation: {Hotkeys.key_to_str(Hotkeys.view_bleed_matrix_calculation)}
                View bled codes: {Hotkeys.key_to_str(Hotkeys.view_bled_codes)}
                View all gene scores: {Hotkeys.key_to_str(Hotkeys.view_all_gene_scores)}
                View gene efficiencies: {Hotkeys.key_to_str(Hotkeys.view_gene_efficiency)}
                View score histogram: {Hotkeys.key_to_str(Hotkeys.view_histogram_scores)}
                View scaled k means: {Hotkeys.key_to_str(Hotkeys.view_scaled_k_means)}
                View spot colour and gene bled code: {Hotkeys.key_to_str(Hotkeys.view_colour_and_codes)}
                View spot intensities: {Hotkeys.key_to_str(Hotkeys.view_spot_intensities)}
                View spot colours and weights: {Hotkeys.key_to_str(Hotkeys.view_spot_colours_and_weights)}
                View intensities calculation from colour: {Hotkeys.key_to_str(Hotkeys.view_intensity_from_colour)}
                View OMP coefficient image: {Hotkeys.key_to_str(Hotkeys.view_omp_coef_image)}"""
        ax.text(
            0.1,
            0.5,
            text,
            fontdict={"size": 12, "verticalalignment": "center", "horizontalalignment": "center"},
            verticalalignment="center",
            horizontalalignment="left",
        )
        fig.show()
