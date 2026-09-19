import os
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.db.session import Base
from app.models.user import User
from app.models.device import Device
from app.models.device_action import DeviceAction
from app.schemas.device import DeviceRegisterRequest
from app.schemas.device_action import RemoteActionDispatchRequest, RemoteActionAckRequest
from app.repositories.device_repository import device_repository
from app.repositories.device_action_repository import device_action_repository

def get_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()

def run_device_action_tests():
    db = get_test_db()
    try:
        # 1. Setup User A and Devices
        user_a_id = uuid.uuid4()
        user_a = User(
            id=user_a_id,
            supabase_user_id=uuid.uuid4(),
            email="usera@vajra.ai",
            full_name="User A",
        )
        db.add(user_a)

        # Setup User B
        user_b_id = uuid.uuid4()
        user_b = User(
            id=user_b_id,
            supabase_user_id=uuid.uuid4(),
            email="userb@vajra.ai",
            full_name="User B",
        )
        db.add(user_b)
        db.commit()

        # Register User A's Phone (Online, has flashlight)
        phone_req = DeviceRegisterRequest(
            device_id="android_phone_001",
            device_type="mobile",
            device_name="Nothing Phone (2a)",
            platform="android",
            app_version="2.0.0",
            capabilities=["call", "sms", "gps", "flashlight", "mobile_alarms"],
        )
        phone_dev = device_repository.register_or_heartbeat(db, user_a_id, phone_req)
        assert phone_dev is not None

        # 2. Test Authorized Dispatch (Flashlight ON)
        dispatch_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.flashlight",
            parameters={"enabled": True},
        )
        action = device_action_repository.dispatch_action(
            db=db,
            user_id=user_a_id,
            req=dispatch_req,
            source_device_id="desktop_win_001",
        )
        assert action is not None
        assert action.status == "PENDING"
        assert action.target_device_id == "android_phone_001"
        assert action.action_type == "device.flashlight"
        assert action.parameters.get("enabled") is True
        print("[PASS] Test 1: Desktop dispatches authorized flashlight ON action (status: PENDING)")

        # 3. Test Cross-User Isolation
        try:
            device_action_repository.dispatch_action(
                db=db,
                user_id=user_b_id,
                req=dispatch_req, # User B trying to target User A's phone
            )
            assert False, "Security Violation: User B was able to target User A's device"
        except HTTPException as e:
            assert e.status_code == 404
            print("[PASS] Test 2: Cross-user isolation verified (User B cannot target User A device)")

        # 4. Test Safety Policy: Arbitrary / Unapproved Actions Blocked
        try:
            bad_req = RemoteActionDispatchRequest(
                target_device_id="android_phone_001",
                action_type="system.shell_exec",
                parameters={"cmd": "rm -rf /"},
            )
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=bad_req)
            assert False, "Security Violation: Arbitrary action was allowed"
        except HTTPException as e:
            assert e.status_code == 400
            assert "not permitted by VAJRA Remote Action Safety Policy" in e.detail
            print("[PASS] Test 3: Safety allowlist verified (arbitrary shell commands blocked)")

        # 5. Test Offline Device Rejection
        # Simulate phone going offline by setting last_seen 10 minutes ago
        phone_dev.last_seen = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()

        try:
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=dispatch_req)
            assert False, "Offline device was incorrectly accepted"
        except HTTPException as e:
            assert e.status_code == 400
            assert "offline" in e.detail.lower()
            print("[PASS] Test 4: Offline device rejected with OFFLINE status")

        # Restore phone online
        phone_dev.last_seen = datetime.now(timezone.utc)
        db.commit()

        # 6. Test Missing Capability Rejection
        phone_without_flash_req = DeviceRegisterRequest(
            device_id="android_phone_noflash",
            device_type="mobile",
            device_name="Old Phone",
            platform="android",
            capabilities=["call", "sms"], # NO flashlight
        )
        device_repository.register_or_heartbeat(db, user_a_id, phone_without_flash_req)

        try:
            noflash_req = RemoteActionDispatchRequest(
                target_device_id="android_phone_noflash",
                action_type="device.flashlight",
                parameters={"enabled": True},
            )
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=noflash_req)
            assert False, "Device without flashlight capability was incorrectly accepted"
        except HTTPException as e:
            assert e.status_code == 400
            assert "does not support required capability" in e.detail
            print("[PASS] Test 5: Missing capability rejected with UNSUPPORTED status")

        # 7. Test Phone Pending Action Retrieval
        pending_actions = device_action_repository.get_pending_actions(
            db=db,
            user_id=user_a_id,
            device_id="android_phone_001",
        )
        assert len(pending_actions) == 1
        retrieved_action = pending_actions[0]
        assert retrieved_action.id == action.id
        assert retrieved_action.status == "SENT"
        print("[PASS] Test 6: Target phone retrieves pending action (status transitioned to SENT)")

        # 8. Test Execution Acknowledgement (SUCCESS)
        ack_success = RemoteActionAckRequest(
            status="SUCCESS",
            result_message="Physical flashlight enabled via CameraManager",
        )
        acked = device_action_repository.acknowledge_action(
            db=db,
            user_id=user_a_id,
            action_id=action.id,
            req=ack_success,
        )
        assert acked is not None
        assert acked.status == "SUCCESS"
        assert acked.result_message == "Physical flashlight enabled via CameraManager"
        assert acked.executed_at is not None
        print("[PASS] Test 7: Mobile posts SUCCESS acknowledgement with execution timestamp")

        # 9. Test Status Polling
        polled = device_action_repository.get_action_by_id(
            db=db,
            user_id=user_a_id,
            action_id=action.id,
        )
        assert polled.status == "SUCCESS"
        print("[PASS] Test 8: Desktop polls and receives SUCCESS acknowledgement")

        # 10. Remote Action Engine 2.0: Test Timer Dispatch
        timer_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.timer",
            parameters={"seconds": 60, "label": "Tea Timer"},
        )
        timer_action = device_action_repository.dispatch_action(
            db=db,
            user_id=user_a_id,
            req=timer_req,
            source_device_id="desktop_win_001",
        )
        assert timer_action.status == "PENDING"
        assert timer_action.action_type == "device.timer"
        print("[PASS] Test 9: Remote Action 2.0 - Timer dispatch succeeded (mobile_alarms capability)")

        # 11. Remote Action Engine 2.0: Missing 'apps' capability initially fails
        app_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.app.open",
            parameters={"app": "chrome", "package": "com.android.chrome"},
        )
        try:
            device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=app_req)
            assert False, "Should have failed because 'apps' capability is not yet registered"
        except HTTPException as e:
            assert e.status_code == 400
            assert "apps" in e.detail
            print("[PASS] Test 10: Remote Action 2.0 - App launch correctly blocked until 'apps' capability registered")

        # 12. Register Full Remote Action 2.0 Capabilities on Phone
        phone_2_req = DeviceRegisterRequest(
            device_id="android_phone_001",
            device_type="mobile",
            device_name="Nothing Phone (2a)",
            platform="android",
            app_version="2.0.0",
            capabilities=["call", "sms", "gps", "flashlight", "mobile_alarms", "media", "settings", "apps"],
        )
        device_repository.register_or_heartbeat(db, user_a_id, phone_2_req)

        # 13. Dispatch Media Control
        media_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.media.play",
            parameters={"command": "play"},
        )
        media_action = device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=media_req)
        assert media_action.status == "PENDING"
        print("[PASS] Test 11: Remote Action 2.0 - Media play dispatch succeeded")

        # 14. Dispatch Settings Control
        settings_req = RemoteActionDispatchRequest(
            target_device_id="android_phone_001",
            action_type="device.settings",
            parameters={"type": "app"},
        )
        settings_action = device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=settings_req)
        assert settings_action.status == "PENDING"
        print("[PASS] Test 12: Remote Action 2.0 - Settings dispatch succeeded")

        # 15. Dispatch App Open (Chrome)
        app_action = device_action_repository.dispatch_action(db=db, user_id=user_a_id, req=app_req)
        assert app_action.status == "PENDING"
        assert app_action.action_type == "device.app.open"
        print("[PASS] Test 13: Remote Action 2.0 - Chrome app open dispatch succeeded")

        # 16. Acknowledge App Open
        app_ack = RemoteActionAckRequest(
            status="SUCCESS",
            result_message="Chrome launched on Nothing Phone (2a)",
        )
        app_acked = device_action_repository.acknowledge_action(
            db=db,
            user_id=user_a_id,
            action_id=app_action.id,
            req=app_ack,
        )
        assert app_acked.status == "SUCCESS"
        assert app_acked.result_message == "Chrome launched on Nothing Phone (2a)"
        print("[PASS] Test 14: Remote Action 2.0 - App open ACK verified")

        print("\nALL BACKEND REMOTE ACTION TESTS PASSED: 100% SUCCESS!")
    finally:
        db.close()

if __name__ == "__main__":
    run_device_action_tests()
