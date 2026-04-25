import pytest
from datetime import datetime, timedelta

from producer.scheduler import (
    get_window,
    get_poll_interval,
    should_fetch_baseline,
    should_poll_corridor,
    get_budget_status
)


# 1. get_window tests


def test_window_morning():
    assert get_window(8) == "MORNING PEAK"

def test_window_midday():
    assert get_window(12) == "MIDDAY"

def test_window_evening():
    assert get_window(18) == "EVENING PEAK"

def test_window_blackout():
    assert get_window(3) == "BLACKOUT"

def test_window_boundary_morning_midday():
    assert get_window(11) == "MIDDAY"

def test_window_boundary_midday_evening():
    assert get_window(16) == "EVENING PEAK"



# 2. get_poll_interval tests


def test_poll_interval_morning():
    assert get_poll_interval(8, 0) == 30

def test_poll_interval_midday():
    assert get_poll_interval(13, 0) == 60

def test_poll_interval_evening():
    assert get_poll_interval(18, 0) == 30

def test_poll_interval_blackout():
    assert get_poll_interval(2, 0) is None

def test_poll_interval_hard_cap():
    assert get_poll_interval(10, 160) is None

def test_poll_interval_emergency_mode():
    # 120 triggers slowdown
    assert get_poll_interval(10, 120) == 60  # 30 * 2



# 3. should_fetch_baseline tests


def test_baseline_runs_at_6am():
    assert should_fetch_baseline(6, False) is True

def test_baseline_skipped_if_done():
    assert should_fetch_baseline(6, True) is False

def test_baseline_not_at_other_hours():
    assert should_fetch_baseline(7, False) is False
    assert should_fetch_baseline(12, False) is False



# 4. should_poll_corridor tests


def test_first_time_always_true():
    assert should_poll_corridor("A", 30, {}) is True

def test_enough_time_passed():
    last = {"A": datetime.now() - timedelta(minutes=40)}
    assert should_poll_corridor("A", 30, last) is True

def test_not_enough_time():
    last = {"A": datetime.now() - timedelta(minutes=10)}
    assert should_poll_corridor("A", 30, last) is False

def test_exact_boundary():
    last = {"A": datetime.now() - timedelta(minutes=30)}
    assert should_poll_corridor("A", 30, last) is True

def test_corridorB_midday():
    last = {"B": datetime.now() - timedelta(minutes=40)}
    assert should_poll_corridor("B", 60, last) is False 




# 5. get_budget_status tests


def test_budget_normal_mode():
    status = get_budget_status(50)
    assert status["mode"] == "NORMAL"
    assert status["calls_remaining"] == 110

def test_budget_emergency_mode():
    status = get_budget_status(130)
    assert status["mode"] == "EMERGENCY"

def test_budget_projection():
    status = get_budget_status(10)
    assert status["monthly_projection"] == 300

def test_budget_free_tier():
    status = get_budget_status(10)
    assert status["within_free_tier"] is True