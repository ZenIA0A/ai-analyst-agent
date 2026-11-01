"""Shared chart style. One restrained palette, validated for colour-blind separation and contrast on white:
blue = the main series, orange = the highlight, teal = a third series, grey = context. Text is black."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, TEAL, GREY = "#1f63b5", "#d9622b", "#23977f", "#9a9a9a"
LIGHT = "#a9c4e8"                      # light tint of the main blue (secondary series of the same kind)
BAND, BAND2 = "#dce7f5", "#f8ddd0"     # fills for uncertainty bands (blue, orange)
INK, INK2, GRID = "#000000", "#404040", "#e5e5e5"
SHADE = "#f2f2f2"                      # background shading for periods
RAMP = ["#dce7f5", "#a9c4e8", "#6f9bd6", "#1f63b5", "#123d70"]   # light -> dark (ordinal)

def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "axes.titleweight": "bold", "axes.titlesize": 10.5,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "legend.frameon": False, "patch.edgecolor": "white", "patch.linewidth": 0.6,
    })

def clean(ax, grid_axis="x"):
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_color(INK2); ax.spines["bottom"].set_color(INK2)

def source(fig, text, y=0.005):
    """Source line in the bottom-left corner of a figure, as in published research notes."""
    fig.text(0.01, y, text, fontsize=7.5, color=INK2, ha="left", va="bottom")
