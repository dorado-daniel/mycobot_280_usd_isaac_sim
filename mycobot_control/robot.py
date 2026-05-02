import omni.usd
from pxr import Usd, UsdPhysics

from .logger import get_logger

_log = get_logger("robot")


class MyCobotRobot:
    def __init__(
        self,
        robot_root_path: str = "/World/mycobot_280_m5",
        joints_scope_name: str = "physics_joints",
        legacy_urdf_joints_scope_name: str = "joints",
    ):
        self.robot_root_path = robot_root_path
        self.joints_path = f"{robot_root_path}/{joints_scope_name}"
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
            if not drive:
                _log.error(f"  MISSING angular DriveAPI on {jp.GetPath()}")
                all_ok = False
            else:
                _log.info(f"  angular DriveAPI OK on {jp.GetPath()}")

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

        _log.info("Validation PASSED.")
        return True
