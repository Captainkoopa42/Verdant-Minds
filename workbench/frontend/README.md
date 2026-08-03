# Verdant Workbench Frontend — 1.0.1 / V5

The checked-in `dist/` directory is the dependency-free reference UI served by the Workbench backend. It includes the operational Organism, Cultivate, Curriculum, Grammar, Explorer, Structures, Evidence, Experiments, Timeline, Connections, and Engineering surfaces.

`src/` contains the React/TypeScript development source. The release runtime does **not** require npm because the reference browser build is already checked in. `package.json` uses explicit package versions for rebuild intent, but this environment's restricted npm registry cannot generate a trustworthy transitive lockfile; rebuilds should generate and commit `package-lock.json` on a normal npm registry before changing the checked-in `dist/`.

Scientific rule: visual state is a projection of recorded engine state/events. Display layout is not asserted to be Verdant's intrinsic cognitive geometry.
