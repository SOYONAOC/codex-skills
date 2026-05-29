---
name: physics-aware-plotting
description: Use when making or updating scientific plots in research repositories. Before plotting, identify the physical meaning of each axis and what comparison the figure is meant to support; when axis limits are not specified, choose physically meaningful limits rather than arbitrary extremes, especially on log scales.
---

# Physics-Aware Plotting

Use this skill for scientific figures, diagnostic plots, and slide/paper plots in these research projects.

## Core workflow

Before plotting, explicitly determine:

1. What physical quantity is on each axis.
2. What comparison or claim the figure is supposed to support.
3. Whether linear or log scaling is physically appropriate.

Do not treat plotting as a purely cosmetic task. The chosen limits, scaling, and overlays should help reveal the physical behavior that matters.

## Default plotting style

When using Matplotlib in these research repositories, default to the configured ApJ style:

```python
import matplotlib.pyplot as plt

plt.style.use('apj')
```

Apply this by default unless the user explicitly requests a different style or the target script already uses a project-specific style setup. If no further styling is specified, rely on the `apj` style configuration for fonts, line widths, ticks, and related defaults rather than re-declaring them manually.

## Axis-range rules

If the user specifies axis limits, follow them.

If limits are not specified:

- Choose ranges from the data and the intended physical message.
- Avoid meaningless empty decades on log axes.
- Do not default to extremely small lower bounds such as `1e-20` unless the plotted quantity actually has meaningful structure there.
- On log y-axes, prefer a lower bound around the smallest meaningful nonzero signal, observational point, or modeled feature that the figure is intended to show.
- Set the upper bound slightly above the maximum relevant curve or data point so the structure is visible without excessive empty space.
- If the figure is meant to compare multiple redshifts, models, or panels, use consistent limits when that improves interpretability.

## Interpretation rules

- Prefer plot layouts that separate different physical concepts instead of overloading one panel.
- If a transformation changes the meaning of the plotted quantity, reflect that in labels and legends.
- Keep legends readable; increase legend size when the plot will be embedded in slides.
- When a figure is for slides or papers, prioritize clarity over showing every diagnostic variant.

## Output placement

Use the `research-project-layout` conventions:

- draft or diagnostic figures: `outputs/`
- reusable tables behind figures: `data_save/`
- figures required by slide compilation: `slides/assets/`

## Slide figure quality

When a figure is intended for slides:

- Treat the slide asset as publication-quality by default.
- Prefer vector `.pdf` output for the figure actually inserted into the slide.
- If a raster companion is generated for quick viewing, export it at `>=500 dpi`.
- Do not treat low-resolution `.png` output as the canonical slide asset unless the user explicitly requests that.

## DPI setting

Always use `dpi=500` in `fig.savefig()` for all figure outputs (both draft and publication). Do not use lower DPI values unless the user explicitly requests otherwise.

## Cleanup rule

When a slide figure is replaced, keep only the currently used asset in `slides/assets/`. Remove stale superseded slide assets and keep one-off or historical plot variants in `outputs/` instead.
