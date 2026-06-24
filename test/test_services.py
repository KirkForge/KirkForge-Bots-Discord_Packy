#!/usr/bin/env python3
"""
Unit tests for Packy services module (scheduler, alarms, reminders, etc.)
"""

import sys
import os
import tempfile
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Ensure we don't accidentally start the global scheduler
os.environ["PACKY_SCHEDULER_DB"] = tempfile.mktemp(suffix=".db")


def test_scheduler_import():
    """Test importing the scheduler module."""
    try:
        from src.cognition.services.scheduler import Scheduler, iso_to_ts, ts_to_iso, now_ts
        print("PASS: scheduler import")
        return True
    except Exception as e:
        print(f"FAIL: scheduler import: {e}")
        return False


def test_iso_to_ts():
    """Test ISO 8601 parsing."""
    try:
        from src.cognition.services.scheduler import iso_to_ts
        # UTC timestamp
        ts = iso_to_ts("2025-01-15T12:00:00+0000")
        assert ts > 0, "Expected positive timestamp"
        # Without timezone (assumes UTC)
        ts2 = iso_to_ts("2025-01-15T12:00:00")
        assert ts2 > 0, "Expected positive timestamp for no-tz"
        # With Z suffix
        ts3 = iso_to_ts("2025-01-15T12:00:00Z")
        assert ts3 > 0, "Expected positive timestamp for Z suffix"
        print("PASS: iso_to_ts")
        return True
    except Exception as e:
        print(f"FAIL: iso_to_ts: {e}")
        return False


def test_scheduler_create_cancel():
    """Test creating and cancelling scheduled jobs."""
    try:
        from src.cognition.services.scheduler import Scheduler
        s = Scheduler(poll_interval_seconds=0.1)
        s.start()
        try:
            result = []
            job_id = s.schedule_delay(0.5, result.append, 42, meta={"test": True})
            assert job_id, "Expected job_id"
            pending = s.get_pending()
            assert len(pending) > 0, "Expected pending jobs"
            found = any(j["job_id"] == job_id for j in pending)
            assert found, f"Job {job_id} not found in pending"
            # Cancel it
            cancelled = s.cancel(job_id)
            assert cancelled, "Expected cancel to succeed"
            # After cancel, job should be gone
            pending2 = s.get_pending()
            assert not any(j["job_id"] == job_id for j in pending2), "Job should be removed after cancel"
            print("PASS: scheduler create/cancel")
            return True
        finally:
            s.stop()
    except Exception as e:
        print(f"FAIL: scheduler create/cancel: {e}")
        return False


def test_scheduler_delay_executes():
    """Test that a delayed job actually executes."""
    try:
        from src.cognition.services.scheduler import Scheduler
        s = Scheduler(poll_interval_seconds=0.05)
        s.start()
        try:
            result = []
            job_id = s.schedule_delay(0.2, result.append, "hello")
            time.sleep(0.5)
            assert result == ["hello"], f"Expected ['hello'], got {result}"
            print("PASS: scheduler delay executes")
            return True
        finally:
            s.stop()
    except Exception as e:
        print(f"FAIL: scheduler delay executes: {e}")
        return False


def test_scheduler_store_crud():
    """Test SchedulerStore CRUD operations."""
    try:
        from src.cognition.services.scheduler import Scheduler
        from src.cognition.services.scheduler_store import SchedulerStore
        
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["PACKY_SCHEDULER_DB"] = db_path
        
        s = Scheduler(poll_interval_seconds=0.1)
        s.start()
        try:
            store = SchedulerStore(scheduler=s, db_path=db_path)
            
            # Create alarm
            alarm = store.create_alarm(
                title="Test Alarm",
                time_iso="2026-06-01T08:00:00+0000",
                payload={"test": True},
                enabled=True,
            )
            assert alarm["title"] == "Test Alarm", f"Expected 'Test Alarm', got {alarm['title']}"
            assert "id" in alarm, "Expected id in alarm"
            
            # List alarms
            alarms = store.list_alarms()
            assert len(alarms) >= 1, f"Expected at least 1 alarm, got {len(alarms)}"
            
            # Delete alarm
            deleted = store.delete_alarm(alarm["id"])
            assert deleted, "Expected delete to succeed"
            
            # Verify deletion
            alarms2 = store.list_alarms()
            assert len(alarms2) == len(alarms) - 1, "Expected one fewer alarm after deletion"
            
            print("PASS: scheduler_store CRUD")
            return True
        finally:
            s.stop()
            # Clean up temp db
            try:
                os.unlink(db_path)
            except OSError:
                pass
    except Exception as e:
        print(f"FAIL: scheduler_store CRUD: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alarms_api():
    """Test the alarms API wrapper."""
    try:
        from src.cognition.services.alarms import create_alarm, list_alarms, delete_alarm
        
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["PACKY_SCHEDULER_DB"] = db_path
        
        # Need to init persistence first
        from src.cognition.services.main import init_persistence, shutdown, _persistence_store
        import src.cognition.services.main as main_mod
        
        # Reset global state for test
        main_mod._persistence_store = None
        
        s = init_persistence(db_path=db_path)
        
        # Create alarm
        result = create_alarm(title="API Test Alarm", time_iso="2026-07-01T09:00:00+0000")
        assert result["ok"], f"Expected ok=True, got {result}"
        assert "alarm" in result, "Expected alarm in result"
        
        # List alarms
        listed = list_alarms()
        assert listed["ok"], f"Expected ok=True for list, got {listed}"
        assert len(listed["alarms"]) >= 1, "Expected at least 1 alarm"
        
        # Delete alarm
        alarm_id = result["alarm"]["id"]
        del_result = delete_alarm(alarm_id)
        assert del_result["ok"], f"Expected ok=True for delete, got {del_result}"
        
        shutdown()
        # Clean up
        try:
            os.unlink(db_path)
        except OSError:
            pass
        
        # Reset for next tests
        main_mod._persistence_store = None
        
        print("PASS: alarms API")
        return True
    except Exception as e:
        print(f"FAIL: alarms API: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reminders_api():
    """Test the reminders API wrapper."""
    try:
        from src.cognition.services.reminders import create_reminder, list_reminders, delete_reminder
        
        db_path = tempfile.mktemp(suffix=".db")
        os.environ["PACKY_SCHEDULER_DB"] = db_path
        
        from src.cognition.services.main import init_persistence, shutdown
        import src.cognition.services.main as main_mod
        main_mod._persistence_store = None
        
        s = init_persistence(db_path=db_path)
        
        # Create reminder
        result = create_reminder(note="Test Reminder", time_iso="2026-08-01T10:00:00+0000")
        assert result["ok"], f"Expected ok=True, got {result}"
        assert "reminder" in result, "Expected reminder in result"
        assert result["reminder"]["title"] == "Test Reminder", "Expected title to match note"
        
        # List reminders
        listed = list_reminders()
        assert listed["ok"], f"Expected ok=True for list, got {listed}"
        assert len(listed["reminders"]) >= 1, "Expected at least 1 reminder"
        
        # Delete reminder
        reminder_id = result["reminder"]["id"]
        del_result = delete_reminder(reminder_id)
        assert del_result["ok"], f"Expected ok=True for delete, got {del_result}"
        
        shutdown()
        try:
            os.unlink(db_path)
        except OSError:
            pass
        main_mod._persistence_store = None
        
        print("PASS: reminders API")
        return True
    except Exception as e:
        print(f"FAIL: reminders API: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quota_store():
    """Test the QuotaStore."""
    try:
        from src.cognition.services.llm_quota_store import QuotaStore
        
        db_path = tempfile.mktemp(suffix=".json")
        store = QuotaStore(path=db_path, daily_limit=100, per_minute_limit=50)
        
        # Try consume
        allowed, info = store.try_consume(1)
        assert allowed, f"Expected allowed=True, got {allowed}, {info}"
        assert info["used_today"] == 1, f"Expected used_today=1, got {info['used_today']}"
        
        # Multiple consumes
        for i in range(5):
            allowed, info = store.try_consume(1)
            assert allowed, f"Consume {i+2} should be allowed"
        
        assert info["used_today"] == 6, f"Expected used_today=6, got {info['used_today']}"
        
        # Usage info
        usage = store.usage_info()
        assert usage["allowed_daily"] == 100
        assert usage["used_today"] == 6
        
        # Clean up
        try:
            os.unlink(db_path)
        except OSError:
            pass
        
        print("PASS: quota store")
        return True
    except Exception as e:
        print(f"FAIL: quota store: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager():
    """Test config load/save."""
    try:
        import json
        from src.cognition.services.config_manager import load_config, save_config, CONFIG_PATH
        
        # Use a temp file for testing
        tmp = tempfile.mktemp(suffix=".json")
        os.environ["CONFIG_PATH"] = tmp
        
        # Reimport to pick up new path
        import importlib
        from src.cognition.services import config_manager
        importlib.reload(config_manager)
        
        # Load empty
        cfg = config_manager.load_config()
        assert "alarms" in cfg, f"Expected 'alarms' key, got {list(cfg.keys())}"
        
        # Save and reload
        cfg["test_key"] = "test_value"
        config_manager.save_config(cfg)
        cfg2 = config_manager.load_config()
        assert cfg2["test_key"] == "test_value", f"Expected test_value, got {cfg2.get('test_key')}"
        
        # Clean up
        try:
            os.unlink(tmp)
        except OSError:
            pass
        
        print("PASS: config manager")
        return True
    except Exception as e:
        print(f"FAIL: config manager: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_env_module():
    """Test the env helper."""
    try:
        from src.cognition.services.env import env
        
        # Test with default
        val = env("NONEXISTENT_VAR_12345", "default_value")
        assert val == "default_value", f"Expected 'default_value', got {val}"
        
        # Test with existing env var
        os.environ["TEST_ENV_VAR"] = "test_val"
        val2 = env("TEST_ENV_VAR")
        assert val2 == "test_val", f"Expected 'test_val', got {val2}"
        del os.environ["TEST_ENV_VAR"]
        
        print("PASS: env module")
        return True
    except Exception as e:
        print(f"FAIL: env module: {e}")
        return False


def test_integration_stubs():
    """Test integration module stubs."""
    try:
        from src.cognition.services.integration import (
            poll_google_calendar, poll_gmail, poll_weather, poll_rss, forward_event
        )
        
        # These are stubs — they should not raise
        poll_google_calendar()
        poll_gmail()
        poll_weather()
        poll_rss()
        forward_event({"title": "test"})
        
        print("PASS: integration stubs")
        return True
    except Exception as e:
        print(f"FAIL: integration stubs: {e}")
        return False


def main():
    """Run all services tests and report results."""
    print("=" * 60)
    print("Packy V2.0.0 Services Unit Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_scheduler_import,
        test_iso_to_ts,
        test_scheduler_create_cancel,
        test_scheduler_delay_executes,
        test_scheduler_store_crud,
        test_alarms_api,
        test_reminders_api,
        test_quota_store,
        test_config_manager,
        test_env_module,
        test_integration_stubs,
    ]
    
    results = []
    for test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"UNEXPECTED ERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
