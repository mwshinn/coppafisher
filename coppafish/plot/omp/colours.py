import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from ...omp.coefs import CoefficientSolverOMP
from ...setup import config
from ...setup.notebook_page import NotebookPage
from ..results_viewer.subplot import Subplot


class ViewOMPColourSum(Subplot):
    def __init__(
        self,
        nbp_basic: NotebookPage,
        nbp_call_spots: NotebookPage,
        nbp_omp: NotebookPage | None,
        method: str,
        local_yxz: np.ndarray[int],
        spot_tile: int,
        spot_colour: np.ndarray[float],
        show: bool = True,
    ) -> None:
        """
        Show the weighted gene bled codes that are summed together by OMP to try and produce the total pixel's colour
        after completing all iterations. It also displays the residual colour left behind that is unaccounted for.

        Args:
            nbp_basic (NotebookPage): `basic_info` notebook page.
            nbp_filter (NotebookPage): `filter` notebook page.
            nbp_register (NotebookPage): `register` notebook page.
            nbp_call_spots (NotebookPage): `call_spots` notebook page.
            nbp_omp (NotebookPage or none): `omp` notebook page or none.
            method (str): gene calling method.
            local_yxz (`(3) ndarray[int]`): the pixel position relative to its tile's bottom-left corner.
            spot_tile (int-like): tile index the pixel is on.
            spot_colour (`(n_rounds_use x n_channels_use) ndarray[float]`): the spot's colour.
            show (bool, optional): display the plot once built. False is useful when unit testing. Default: true.
        """
        n_rounds_use = len(nbp_basic.use_rounds)
        n_channels_use = len(nbp_basic.use_channels)
        min_intensity = config.get_default_for("omp", "minimum_intensity")
        max_genes = config.get_default_for("omp", "max_genes")
        dot_product_threshold = config.get_default_for("omp", "dot_product_threshold")
        self.gene_names = nbp_call_spots.gene_names
        if nbp_omp is not None:
            min_intensity = float(nbp_omp.associated_configs["omp"]["minimum_intensity"])
            max_genes = int(nbp_omp.associated_configs["omp"]["max_genes"])
            dot_product_threshold = float(nbp_omp.associated_configs["omp"]["dot_product_threshold"])

        self.colour = spot_colour.copy().astype(np.float32)
        self.colour *= nbp_call_spots.colour_norm_factor[[spot_tile]].astype(np.float32)
        omp_solver = CoefficientSolverOMP()
        bled_codes = nbp_call_spots.bled_codes.astype(np.float32)
        bg_bled_codes = omp_solver.create_background_bled_codes(n_rounds_use, n_channels_use)
        coefficients, gene_weights = omp_solver.solve(
            pixel_colours=self.colour[np.newaxis],
            bled_codes=bled_codes,
            background_codes=bg_bled_codes,
            maximum_iterations=max_genes,
            dot_product_threshold=dot_product_threshold,
            minimum_intensity=min_intensity,
            return_all_weights=True,
        )
        coefficient = coefficients[0]
        gene_weight = gene_weights[0]
        self.assigned_genes: np.ndarray[int] = (~np.isnan(gene_weight)).nonzero()[0]
        gene_weight = gene_weight[self.assigned_genes]
        coefficient = coefficient[self.assigned_genes]
        n_iterations = self.assigned_genes.size
        assert n_iterations > 0
        self.assigned_bled_codes = nbp_call_spots.bled_codes[self.assigned_genes]
        # Weight the bled codes.
        self.assigned_bled_codes *= gene_weight
        self.residual_colour = self.colour - self.assigned_bled_codes
        abs_max = np.abs(self.assigned_bled_codes).max()
        abs_max = np.max([abs_max, np.abs(self.colour).max()])
        abs_max = np.max([abs_max, np.abs(self.residual_colour).max()]).item()

        self.fig, self.axes = plt.subplots(2, max(2, self.assigned_genes.size))
        self.cmap = mpl.cm.seismic
        self.norm = mpl.colors.Normalize(vmin=-abs_max, vmax=abs_max)
        self.draw_data()
        self.fig.suptitle(f"{method.capitalize()} spot at {tuple(local_yxz)} OMP colour sum")
        if show:
            self.fig.show()

    def draw_data(self) -> None:
        for ax in self.axes.ravel():
            ax.clear()
            ax.spines.set_visible(False)

        for i, g in enumerate(self.assigned_genes):
            self.axes[0, i].set_title(f"{self.gene_names[g]}")
            self.axes[0, i].imshow(self.assigned_bled_codes.T, cmap=self.cmap, norm=self.norm)

        self.axes[1, -1].set_title(f"Total colour")
        self.axes[1, -1].imshow(self.colour, cmap=self.cmap, norm=self.norm)
        self.axes[1, -2].set_title(f"Residual colour")
        self.axes[1, -2].imshow(self.residual_colour, cmap=self.cmap, norm=self.norm)

        self.fig.canvas.draw_idle()
