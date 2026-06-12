# MyCobot Control

Kit extension: validation and joint-level control for the MyCobot 280 M5 USD rigs.

## Requirements

- Open `mycobot_280_m5.usd` or `mycobot_280_m5_gripper.usd`.
- Simulation **Play** must be running for drives to move the robot.

## Gripper and mimic

The gripper is **1 DOF** (`gripper_controller`, −42.4° … +8.6°). Five finger joints use **`newton:mimicJoint`**.

- **PhysX (default):** mimic is **not** applied by the solver. Use this extension’s gripper buttons/slider, or set all six joint drive targets in code.
- **Newton:** launch with `isaac-sim.newton.sh`; then a single `gripper_controller` target is enough.

## Controls

- **Validate Robot** — articulation, drives, legacy scope, gripper limits
- **Print Joints** — list `physics_joints`
- **Open / Close / Neutral / slider** — coordinated gripper targets (works under PhysX)
