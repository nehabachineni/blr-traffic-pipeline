import pytest
from unittest.mock import patch
from datetime import datetime

import producer.main as main

#-------------HELPER FUNCTIONS------------------------------------------------------

#reset global state before each test, main.py is stateful 
@pytest.fixture
def reset_state():
    main.baseline_done = False
    main.calls_today = 0
    main.baseline_cache = {}
    main.last_polled = {}
    main.baseline_backup = {}           #only reset for tests





def fake_corridors():
    return[

        {"route_id": f"r{i}", "origin": {}, "destination": {}} for i in range (1,6)
    ]



#---------TESTS------------------------------------------------------------------------


#1 happy path for baseline , all fine , pushed to cache

@patch("producer.main.get_travel_time")
def test_fetch_baseline_all_ok(mock_api, reset_state):

    def api_ok(c):
        return {
            "status": "ok",
            "ETA": 100,
            "route_id": c["route_id"],
            "charged_attempts": 1
        }
    mock_api.side_effect = api_ok #assigning the function, arguments (c) will come in from the original func call

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.fetch_baseline()

    assert len(main.baseline_cache) == 5
    assert main.calls_today == 5
    assert main.baseline_done is True


#2 baseline , mixed api responses, push to dlq + cache

@patch("producer.main.publish_to_dlq")
@patch("producer.main.get_travel_time")
def test_fetch_baseline_mixed(mock_api,mock_dlq,reset_state):

    def api_mixed(c):
        rid = c["route_id"]
        if rid == "r1":
            return {"status": "ok", "ETA": 100, "route_id": rid, "charged_attempts": 1}
        elif rid == "r2":
            return {"status": "dlq", "reason": "NO_ROUTES", "route_id": rid, "charged_attempts": 1}
        else:
            return {"status": "failed", "reason": "TIMEOUT", "route_id": rid, "charged_attempts": 0}

    mock_api.side_effect = api_mixed

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.fetch_baseline()

    assert len(main.baseline_cache) == 1     #only 1 with status ok
    assert mock_dlq.call_count ==1           #only one dlq (rid r2)
    assert main.calls_today == 2             #3 failed calls


#3 happy path for poll corridors, variations in baseline cache

@patch("producer.main.should_poll_corridor", return_value=True)
@patch("producer.main.publish_event")
@patch("producer.main.get_travel_time")
def test_poll_success(mock_api, mock_pub, mock_should, reset_state):

    def api_ok(c):
        return {
            "status": "ok",
            "ETA": 120,
            "route_id": c["route_id"],
            "charged_attempts": 1
        }

    mock_api.side_effect = api_ok
    mock_pub.return_value = True

    main.baseline_cache = {"r1": 60}  # partial baseline
    main.baseline_backup = {}

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    calls = mock_pub.call_args_list
    assert len(calls) == 5

    payload_r1 = calls[0][0][1]   #r1->.args->payload_dict
    payload_r4 = calls[3][0][1]

    assert mock_pub.call_count == 5
    assert main.calls_today == 5
    assert len(main.last_polled) == 5
    
    assert payload_r1["base_time_seconds"] == 60
    assert payload_r1["ratio"] == 2.0               #120/60 (live/base)

    assert payload_r4["base_time_seconds"] is None    # r2,r3,r5 must follow the same, 
    assert payload_r4["ratio"] is None              


# 4 all go to dlq , poll corridors 

@patch("producer.main.should_poll_corridor", return_value=True)
@patch("producer.main.publish_to_dlq")
@patch("producer.main.get_travel_time")
def test_poll_dlq(mock_api, mock_dlq, mock_should, reset_state):

    def api_dlq(c):
        return {
            "status": "dlq",
            "reason": "NO_ROUTES",
            "route_id": c["route_id"],
            "charged_attempts": 1
        }

    mock_api.side_effect = api_dlq
    mock_dlq.return_value = True

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    assert mock_dlq.call_count == 5
    assert main.calls_today == 5
    assert len(main.last_polled) == 5


#5 all failed, no calls today counted, poll corridor

@patch("producer.main.should_poll_corridor", return_value=True)
@patch("producer.main.get_travel_time")
def test_poll_failed(mock_api, mock_should, reset_state):

    def api_fail(c):
        return {
            "status": "failed",
            "reason": "TIMEOUT",
            "route_id": c["route_id"],
            "charged_attempts": 0
        }

    mock_api.side_effect = api_fail

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    assert main.calls_today == 0
    assert len(main.last_polled) == 0


#6 poll corridor mixed api responses, 

@patch("producer.main.publish_event")
@patch("producer.main.publish_to_dlq")
@patch("producer.main.get_travel_time")
def test_fetch_poll_mixed(mock_api,mock_dlq,mock_event,reset_state):

    def api_mixed(c):
        rid = c["route_id"]
        if rid == "r1":
            return {"status": "ok", "ETA": 100, "route_id": rid, "charged_attempts": 1}
        elif rid == "r2":
            return {"status": "dlq", "reason": "NO_ROUTES", "route_id": rid, "charged_attempts": 1}
        else:
            return {"status": "failed", "reason": "TIMEOUT", "route_id": rid, "charged_attempts": 0}

    mock_api.side_effect = api_mixed
    mock_dlq.return_value = True
    mock_event.return_value = True



    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    assert mock_event.call_count ==1 
    assert mock_dlq.call_count ==1              #only one dlq (rid r2)
    assert main.calls_today == 2             #3 failed calls




#7 must fall back on baseline , when cache not available only

@patch("producer.main.should_poll_corridor", return_value=True)
@patch("producer.main.publish_event")
@patch("producer.main.get_travel_time")
def test_fallback_baseline(mock_api, mock_pub, mock_should, reset_state):

    def api_ok(c):
        return {
            "status": "ok",
            "ETA": 200,
            "route_id": c["route_id"],
            "charged_attempts": 1
        }

    mock_api.side_effect = api_ok
    mock_pub.return_value = True

    main.baseline_cache = {"r4" : 100}               
    main.baseline_backup = {"r1": 100, "r4" :200}     # fallback exists

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    calls = mock_pub.call_args_list

    payload_r1 = calls[0][0][1]   #r1->.args->payload_dict
    payload_r4 = calls[3][0][1]
    payload_r5 = calls[4][0][1]


    assert mock_pub.call_count == 5
    assert main.calls_today == 5
    assert len(main.last_polled) == 5

    assert payload_r1["base_time_seconds"] == 100
    assert payload_r1["ratio"] == 2.0        

    assert payload_r4["base_time_seconds"] == 100
    assert payload_r4["ratio"] == 2.0   


    assert payload_r5["base_time_seconds"] is None    # r2,r3 must follow the same, 
    assert payload_r5["ratio"] is None        


#8 test when baseline is 0/none

@patch("producer.main.should_poll_corridor", return_value=True)
@patch("producer.main.publish_event")
@patch("producer.main.get_travel_time")
def test_zero_baseline(mock_api, mock_pub, mock_should, reset_state):

    def api_ok(c):
        return {
            "status": "ok",
            "ETA": 200,
            "route_id": c["route_id"],
            "charged_attempts": 1
        }

    mock_api.side_effect = api_ok
    mock_pub.return_value = True

    main.baseline_cache = {"r1": 0, "r4" : 100}

    with patch("producer.main.CORRIDORS", fake_corridors()):
        main.poll_corridors(interval=5)

    calls = mock_pub.call_args_list
    payload_r1 = calls[0][0][1]   #r1->.args->payload_dict
    payload_r4 = calls[3][0][1]

    assert len(calls) == 5

    assert payload_r1["base_time_seconds"] == None
    assert payload_r1["ratio"] == None   

    assert payload_r4["base_time_seconds"] == 100
    assert payload_r4["ratio"] == 2.0



#9 reset logic check

def test_midnight_reset(reset_state):

    main.calls_today = 10
    main.baseline_done = True
    main.baseline_cache = {"r1": 100}
    main.last_polled = {"r1": datetime.now()}

    today = datetime.now().date()

    main.midnight_reset(today)

    assert main.calls_today == 0
    assert main.baseline_done is False
    assert main.baseline_cache == {}
    assert main.last_polled == {}



