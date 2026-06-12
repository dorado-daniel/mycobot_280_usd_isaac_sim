# mycobot_280_usd_isaac_sim

Self-contained **USD** assets and a **Kit extension** for the Elephant Robotics **MyCobot 280 M5** in NVIDIA Isaac Sim.

Both USD files are flattened: geometry, materials, and physics are baked in. No external mesh files are required after clone.

## Contents

| Path | Description |
|---|---|
| `mycobot_280_m5.usd` | 6-DOF arm only |
| `mycobot_280_m5_gripper.usd` | Arm + adaptive gripper |
| `config/` + `mycobot_control/` | **MyCobot Control** Kit extension |

```
.
├── config/extension.toml
├── docs/README.md
├── mycobot_control/
├── mycobot_280_m5.usd
└── mycobot_280_m5_gripper.usd
```

## Physics model

Both assets share the same articulation root: `/World/mycobot_280_m5`.

| Property | Value |
|---|---|
| Articulation root | `/World/mycobot_280_m5` |
| Controlled joints | `/World/mycobot_280_m5/physics_joints/*` |
| Legacy URDF scope | `/World/mycobot_280_m5/joints` — must stay **deactivated** |
| Joint limits | **degrees** (Isaac Sim convention for this asset) |
| Collision | `convexHull` on all dynamic link meshes |
| Self-collisions | **disabled** on the articulation root (gripper convex hulls overlap at rest) |

Each revolute joint uses **PhysX angular DriveAPI** (`type=force`, stiffness/damping/maxForce, `targetPosition` in degrees).

### Arm joints (6 DOF)

| Joint | Lower | Upper |
|---|---:|---:|
| `joint2_to_joint1` | −168.0° | 168.0° |
| `joint3_to_joint2` | −140.0° | 140.0° |
| `joint4_to_joint3` | −150.0° | 150.0° |
| `joint5_to_joint4` | −150.0° | 150.0° |
| `joint6_to_joint5` | −155.0° | 160.0° |
| `joint6output_to_joint6` | −180.0° | 180.0° |

Control: set **Drive → Angular → Target Position** (degrees) on the joint prim under `physics_joints`, with simulation **Play** running.

## Gripper (1 DOF + mimic)

The adaptive gripper has **one actuated joint** and **five coupled finger joints**, matching the real hardware / URDF mimic chain.

| Joint | Role | Limits (deg) | Mimic of `gripper_controller` |
|---|---|---:|---|
| `gripper_controller` | **Actuated** (master) | −42.4 … +8.6 | — |
| `gripper_base_to_gripper_left2` | Finger | −45.8 … +28.6 | × +1 |
| `gripper_left3_to_gripper_left1` | Finger | −28.6 … +28.6 | × −1 |
| `gripper_base_to_gripper_right3` | Finger | −28.6 … +40.1 | × −1 |
| `gripper_base_to_gripper_right2` | Finger | −28.6 … +45.8 | × −1 |
| `gripper_right3_to_gripper_right1` | Finger | −28.6 … +28.6 | × +1 |

Finger coupling is stored as **`newton:mimicJoint`** on each slave joint (reference → `gripper_controller`, coef0/coef1 = offset / multiplier).

### Mimic is required for correct gripper motion

> **Important:** Under the default **PhysX** backend, `newton:mimicJoint` is **not enforced**. Moving only `gripper_controller → targetPosition` moves a single finger link; the rest will not follow.

Use one of these approaches:

1. **Newton backend (native mimic)** — launch Isaac Sim with Newton so mimic joints are solved automatically:
   ```bash
   ./isaac-sim.newton.sh
   ```
   Then control only `gripper_controller` (Target Position in degrees, range −42.4 … +8.6).

2. **MyCobot Control extension (PhysX)** — sets coordinated drive targets on all six gripper joints from one UI slider / Open / Close buttons.

3. **Custom code / RL env (PhysX or Newton)** — expose **one gripper action** and propagate targets:
   ```python
   # theta = gripper_controller angle in degrees
   set_target("gripper_controller", theta)
   set_target("gripper_base_to_gripper_left2", +theta)
   set_target("gripper_left3_to_gripper_left1", -theta)
   set_target("gripper_base_to_gripper_right3", -theta)
   set_target("gripper_base_to_gripper_right2", -theta)
   set_target("gripper_right3_to_gripper_right1", +theta)
   ```

Suggested mapping: **closed ≈ −42.4°**, **neutral = 0°**, **open ≈ +8.6°** (some finger joints hit their own limits before the controller limit).

For RL, treat the gripper as **one action dimension** (6 arm + 1 gripper). Mimic propagation belongs in the env step, unless you run Newton.

## Install the extension

**Option A — symlink into Isaac’s user extensions folder** (recommended):

```bash
ln -sfn /path/to/mycobot_280_usd_isaac_sim \
  ~/apps/isaacsim-6.0.0/extsUser/mycobot.control
```

**Option B — Extension Search Path:** in **Window → Extensions → gear**, add the **parent** directory of this repo.

Then enable **MyCobot Control** and optionally **Autoload**.

## Usage

1. **File → Open** → `mycobot_280_m5_gripper.usd` (or arm-only USD).
2. Press **Play**.
3. Open **MyCobot Control** (extension window).

Extension default robot path: `/World/mycobot_280_m5`. Override in code via `MyCobotRobot(robot_root_path=...)`.

### Extension UI

| Control | Action |
|---|---|
| **Validate Robot** | Checks stage, `physics_joints`, DriveAPI on revolute joints, legacy `joints` scope deactivated, gripper limits |
| **Print Joints** | Lists joints under `physics_joints` |
| **Open / Close / Neutral** | Sets coordinated gripper targets (PhysX-safe) |
| **Slider** | 0 = closed limit, 1 = open limit |

## Logging

```python
from mycobot_control.logger import get_logger
log = get_logger("my_component")
log.info("hello")
```

Output goes to the in-window log panel, Isaac Console (`carb`), and stdout.
