# mycobot_280_usd_isaac_sim

USD asset and Isaac Sim Kit extension for the **MyCobot 280 M5** robot arm.

This repository contains:

- `mycobot_280_m5.usd` — flattened, self-contained USD rig of the
  MyCobot 280 M5 (imported from URDF, with the `physics_joints` scope
  used for control and the legacy URDF `joints` scope kept deactivated).
  Meshes and materials are baked into the file, so the asset works
  standalone after cloning.
- `mycobot_control/` and `config/` — the **MyCobot Control** Kit
  extension, a small read-only control and validation window for the
  rig.

## Repository layout

```
.
├── config/
│   └── extension.toml              # Kit extension manifest
├── mycobot_control/
│   ├── __init__.py
│   ├── extension.py                # Extension entry point
│   ├── logger.py                   # Centralized logging (carb + UI panel)
│   ├── robot.py                    # USD inspection / validation helpers
│   └── ui.py                       # MyCobot Control window + log panel
└── mycobot_280_m5.usd              # Robot USD asset (flattened)
```

## Installing the extension in Isaac Sim

1. Open Isaac Sim.
2. Go to **Window → Extensions**.
3. Click the gear icon and add the **parent** folder of this repository
   to the *Extension Search Paths*. For example, if the repo is cloned
   to `C:\dev\mycobot_280_usd_isaac_sim`, add `C:\dev` (Kit looks for
   extensions one level below each search path).
4. Search for **MyCobot Control** in the Extensions list and enable it.
   Tick *Autoload* if you want it to start with Isaac Sim.

After enabling the extension you should see a new window titled
**MyCobot Control**.

## Loading the robot

1. In Isaac Sim, **File → Open** and choose `mycobot_280_m5.usd` (or
   drag-and-drop it into the Stage).
2. The default robot root path expected by the extension is
   `/World/mycobot_280_m5`. If your stage uses a different prim path,
   open `mycobot_control/robot.py` and adjust the `robot_root_path`
   default, or instantiate `MyCobotRobot(robot_root_path=...)` with the
   right path.

## Using the MyCobot Control window

The window exposes two buttons and an embedded log panel:

- **Validate Robot** — checks that:
  - a USD stage is open,
  - the robot root prim exists,
  - the `physics_joints` scope and joint prims exist,
  - every revolute joint has an `angular` `DriveAPI` applied,
  - the legacy URDF `joints` scope is **deactivated** (this scope is
    created by the URDF importer and cannot be deleted, only
    deactivated).
- **Print Joints** — lists every joint prim under
  `/World/mycobot_280_m5/physics_joints` with its USD type.

All output appears in the **Log** area inside the window (color-coded by
severity: gray = info, blue = warn, red = error). Messages are also
forwarded to the Isaac Sim Console window and to stdout (terminal).

## Logging

The extension uses a small reusable logger in `mycobot_control/logger.py`:

```python
from mycobot_control.logger import get_logger

log = get_logger("my_component")
log.info("hello")
log.warn("careful")
log.error("nope")
```

Every call fans out to:

- `carb.log_*` (Isaac Sim Console / log file),
- `print(..., flush=True)` (terminal),
- registered subscribers (the in-window log panel uses this).
