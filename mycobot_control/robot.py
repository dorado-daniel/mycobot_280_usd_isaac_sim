import math

import omni.usd
from pxr import Usd, UsdPhysics

from .logger import get_logger

_log = get_logger("robot")

GRIPPER_CONTROLLER = "gripper_controller"


class MyCobotRobot:
    def __init__(
        self,
        robot_root_path: str = "/World/mycobot_280_m5",
        joints_scope_name: str = "physics_joints",
        legacy_urdf_joints_scope_name: str = "joints",
    ):
        self.robot_root_path = robot_root_path
        self.joints_path = f"{robot_root_path}/{joints_scope_name}"
        self.gripper_controller_path = f"{self.joints_path}/{GRIPPER_CONTROLLER}"
        # Scope that the URDF importer creates and that we want kept deactivated
        # (it cannot be deleted, only deactivated).
        self.legacy_joints_path = f"{robot_root_path}/{legacy_urdf_joints_scope_name}"

    def get_stage(self) -> Usd.Stage:
        ctx = omni.usd.get_context()
        return ctx.get_stage() if ctx is not None else None

    def get_joint_scope(self) -> Usd.Prim:
        stage = self.get_stage()
        if stage is None:
            return None
        prim = stage.GetPrimAtPath(self.joints_path)
        return prim if prim and prim.IsValid() else None

    def list_joints(self) -> list:
        scope = self.get_joint_scope()
        if scope is None:
            _log.warn(f"Joint scope not found at {self.joints_path}")
            return []
        joints = []
        for child in scope.GetChildren():
            if child.IsA(UsdPhysics.Joint):
                joints.append(child)
        _log.info(f"Found {len(joints)} joint prim(s) under {self.joints_path}:")
        for j in joints:
            type_name = j.GetTypeName()
            _log.info(f"  - {j.GetPath()} ({type_name})")
        return joints

    def validate(self) -> bool:
        stage = self.get_stage()
        if stage is None:
            _log.error("Validation FAILED: no USD stage is currently open.")
            return False
        _log.info("Stage OK.")

        root = stage.GetPrimAtPath(self.robot_root_path)
        if not root or not root.IsValid():
            _log.error(
                f"Validation FAILED: robot root not found at {self.robot_root_path}"
            )
            return False
        _log.info(f"Robot root OK: {self.robot_root_path}")

        scope = stage.GetPrimAtPath(self.joints_path)
        if not scope or not scope.IsValid():
            _log.error(
                f"Validation FAILED: physics_joints not found at {self.joints_path}"
            )
            return False
        _log.info(f"physics_joints scope OK: {self.joints_path}")

        joint_prims = [c for c in scope.GetChildren() if c.IsA(UsdPhysics.Joint)]
        if not joint_prims:
            _log.error(f"Validation FAILED: no joint prims under {self.joints_path}")
            return False
        _log.info(f"Joint prims OK: {len(joint_prims)} found.")

        all_ok = True
        for jp in joint_prims:
            if not jp.IsA(UsdPhysics.RevoluteJoint):
                continue
            drive = UsdPhysics.DriveAPI.Get(jp, "angular")
            is_mimic = bool(
                jp.HasAttribute("newton:mimicEnabled")
                and jp.GetAttribute("newton:mimicEnabled").Get()
            )
            if drive:
                _log.info(f"  angular DriveAPI OK on {jp.GetName()}")
            elif is_mimic:
                # Mimic-coupled finger joints are driven indirectly; allowed.
                _log.warn(f"  {jp.GetName()} is mimic-coupled (no direct drive) — OK")
            else:
                _log.error(f"  MISSING angular DriveAPI on {jp.GetPath()}")
                all_ok = False

        if not all_ok:
            _log.error(
                "Validation FAILED: one or more revolute joints missing angular DriveAPI."
            )
            return False

        legacy = stage.GetPrimAtPath(self.legacy_joints_path)
        if not legacy or not legacy.IsValid():
            _log.info(
                f"Legacy URDF joints scope not present at {self.legacy_joints_path} (OK)."
            )
        elif legacy.IsActive():
            _log.error(
                f"Validation FAILED: legacy URDF scope {self.legacy_joints_path} "
                "is ACTIVE. It must be deactivated (right click > Deactivate)."
            )
            return False
        else:
            _log.info(
                f"Legacy URDF joints scope deactivated OK: {self.legacy_joints_path}"
            )

        grip = stage.GetPrimAtPath(self.gripper_controller_path)
        if grip and grip.IsValid():
            limits = self.get_gripper_limits()
            mimic = self._mimic_joints()
            if limits is not None:
                _log.info(
                    f"Gripper OK: controller '{GRIPPER_CONTROLLER}' limits "
                    f"[{limits[0]:.1f}, {limits[1]:.1f}] deg, "
                    f"{len(mimic)} coupled finger joint(s)."
                )
        else:
            _log.info("No gripper in this asset (arm-only USD).")

        _log.info("Validation PASSED.")
        return True

    # ------------------------------------------------------------------
    # Gripper control
    # ------------------------------------------------------------------
    def _get_revolute(self, path: str) -> Usd.Prim:
        stage = self.get_stage()
        if stage is None:
            return None
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid() and prim.IsA(UsdPhysics.RevoluteJoint):
            return prim
        return None

    def get_gripper_limits(self):
        """Return (lower, upper) drive limits of the gripper controller in degrees."""
        prim = self._get_revolute(self.gripper_controller_path)
        if prim is None:
            return None
        rj = UsdPhysics.RevoluteJoint(prim)
        return (rj.GetLowerLimitAttr().Get(), rj.GetUpperLimitAttr().Get())

    def _mimic_joints(self):
        """Return [(prim, multiplier, offset_deg)] for joints coupled to the controller."""
        scope = self.get_joint_scope()
        out = []
        if scope is None:
            return out
        for child in scope.GetChildren():
            enabled = child.HasAttribute("newton:mimicEnabled") and child.GetAttribute(
                "newton:mimicEnabled"
            ).Get()
            if not enabled:
                continue
            mult = child.GetAttribute("newton:mimicCoef1").Get() or 0.0
            offset = child.GetAttribute("newton:mimicCoef0").Get() or 0.0
            out.append((child, float(mult), math.degrees(float(offset))))
        return out

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def set_gripper_target(self, angle_deg: float) -> bool:
        """Command the gripper controller (deg) and coordinate coupled fingers.

        Works whether the sim is stopped or playing: the drive targetPosition
        attribute is synced to PhysX. Targets are clamped to each joint's limits.
        """
        ctrl = self._get_revolute(self.gripper_controller_path)
        if ctrl is None:
            _log.error(
                "Gripper controller not found. Load mycobot_280_m5_gripper.usd "
                f"(expected joint at {self.gripper_controller_path})."
            )
            return False

        rj = UsdPhysics.RevoluteJoint(ctrl)
        lo, hi = rj.GetLowerLimitAttr().Get(), rj.GetUpperLimitAttr().Get()
        target = self._clamp(angle_deg, lo, hi)

        drive = UsdPhysics.DriveAPI.Get(ctrl, "angular")
        if not drive:
            _log.error("Gripper controller has no angular DriveAPI.")
            return False
        drive.CreateTargetPositionAttr().Set(target)
        _log.info(
            f"gripper_controller target = {target:.1f} deg (limits [{lo:.1f}, {hi:.1f}])."
        )

        for prim, mult, offset_deg in self._mimic_joints():
            cj = UsdPhysics.RevoluteJoint(prim)
            jlo, jhi = cj.GetLowerLimitAttr().Get(), cj.GetUpperLimitAttr().Get()
            coupled = self._clamp(target * mult + offset_deg, jlo, jhi)
            d = UsdPhysics.DriveAPI.Get(prim, "angular")
            if d:
                d.CreateTargetPositionAttr().Set(coupled)
        return True

    def open_gripper(self) -> bool:
        limits = self.get_gripper_limits()
        if limits is None:
            return self.set_gripper_target(0.0)
        return self.set_gripper_target(limits[1])

    def close_gripper(self) -> bool:
        limits = self.get_gripper_limits()
        if limits is None:
            return self.set_gripper_target(0.0)
        return self.set_gripper_target(limits[0])

    def set_gripper_fraction(self, fraction: float) -> bool:
        """0.0 -> lower limit, 1.0 -> upper limit."""
        limits = self.get_gripper_limits()
        if limits is None:
            return False
        lo, hi = limits
        return self.set_gripper_target(lo + self._clamp(fraction, 0.0, 1.0) * (hi - lo))
