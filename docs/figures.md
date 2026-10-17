# Figures

A figure is a drawing of the thing a lesson teaches, kept as pack content (see
`content-schema.md`, Figures). This is how one is made.

## Where a figure lives

```
content/packs/<pack>/figures/<slug>.py    the source: a mingrammer/diagrams script
content/packs/<pack>/figures/<slug>.svg   the drawing it writes, committed
content/packs/<pack>/pack.json            the figure item, `"file": "figures/<slug>.svg"`
```

The item carries the title, the caption (the decision rule the drawing shows, a sentence or
two), the alt text, the objectives it serves, the source it was checked against and the
provenance, like any item. A lesson shows it by listing the slug in `figures` and may place
it in its body with `![alt](figure:slug)`.

## Drawing

Figures are drawn with [mingrammer/diagrams](https://github.com/mingrammer/diagrams) on
Graphviz, which ships the official AWS and Kubernetes icons. Install Graphviz once
(`brew install graphviz` on macOS); the Python side is the `figures` dependency group,
which `make figures` installs on demand and the image never carries.

A script draws one figure and writes the SVG beside itself with its icons inlined
(`figures/vpc-two-tier.py` is the model). Conventions, so the drawings read as one set:

- One thing per figure, the thing the exam asks about; a caption that states the decision
  rule, not a description of the boxes.
- Direction left to right for request flows, top to bottom for hierarchies; clusters for
  the boundaries that matter (VPC, subnets, accounts, Regions); dashed edges for control
  or out-of-band paths, labelled only where the label is the point.
- Short node labels in sentence case; the service's own name (Application Load Balancer,
  not ALB) the first time it appears in a lesson's set.
- No text that will date (prices, limits); those live in the lesson with a checked source.

## Commands

```bash
make figures                 # draw every pack's figures from their scripts
make figures PACK=<slug>     # one pack
make figures-check           # re-draw into scratch and compare with the committed SVGs
```

`render` runs each script in place, then rewrites the node ids the library draws at random
into `n1, n2, ...` and drops the generator's comments, so the committed SVG changes only
when the drawing changes; it then validates each pack it touched, so a drawing with a script
tag or an external reference is refused on the spot. `check` renders each script in a
scratch copy and compares; it is the step to run before committing a figure and belongs in
CI once the runner has Graphviz. The SVG is the artifact the app serves; the script is the
source to edit.

## Reviewing

Figures are items: the Content page lists them (`kind: figure`), the item page shows the
drawing with its caption, and `review_status` moves from `source_checked` to
`human_reviewed` when the owner has looked. A figure attaches to objectives, never to a
course or a lecture, so lectures mapped to the same objectives borrow it.
