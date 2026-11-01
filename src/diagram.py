"""Architecture diagram of the agent and its controls."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import style as st

st.setup()
fig, ax = plt.subplots(figsize=(10.5, 4.3)); ax.set_xlim(0, 105); ax.set_ylim(0, 43); ax.axis("off")
def box(x, y, w, h, text, fill="#ffffff", edge=st.GREY, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fill, ec=edge, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.8, fontweight="bold" if bold else "normal", color=st.INK)
def arrow(x1, y1, x2, y2, text=None, dy=1.6):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="->", color=st.INK2, lw=1.2))
    if text: ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, text, ha="center", fontsize=8, color=st.INK2)
box(1, 17, 15, 9, "Analyst\nasks a question", "#f2f2f2")
box(25, 17, 20, 9, "Language model\nrules + table catalogue\nreplies in JSON only", "#e6f0fc", st.BLUE, True)
box(52, 30, 22, 9, "Tool layer\nget_series  summarise\ngroup_snapshot  calculate", "#ffffff", st.GREY)
box(81, 30, 22, 9, "Real data tables\nRBA A2, E2, F5\nAPRA property exposures", "#ffffff", st.GREY)
box(81, 17, 22, 9, "Grounding guard\nanswer must match a\ntool result, else retry\nor refuse", "#fdeee8", st.ORANGE, True)
box(81, 3, 22, 8, "Answer, or\n'cannot answer'", "#f2f2f2")
arrow(16, 21.5, 25, 21.5)
arrow(45, 25, 52, 32)
ax.text(40.5, 30.5, "tool call", fontsize=8, color=st.INK2)
arrow(52, 36, 45, 26.5)
arrow(74, 34.5, 81, 34.5, "reads", dy=1.2)
arrow(45, 21.5, 81, 21.5, "final answer", dy=1.4)
arrow(92, 17, 92, 11)
ax.text(1, 41.5, "Tool results are treated as data, never as instructions", ha="left", fontsize=8.3, color=st.INK2, style="italic")
ax.text(1, 3.5, "Every question, tool call, result and final answer is logged for audit", ha="left", fontsize=8.3, color=st.INK2, style="italic")
fig.tight_layout(); fig.savefig("outputs/fig0_architecture.png", dpi=200); print("ok")
