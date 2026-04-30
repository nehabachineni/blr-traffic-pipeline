from unittest.mock import patch
from producer.api_client import get_travel_time
import pytest,requests


@pytest.fixture       #decorator for reusable data for independent tests, pytest auto injects it based on name
def corridor():
    return{
        "route_id": "test",
        "origin": {"lat": 1.0, "lng": 2.0},
        "destination": {"lat": 3.0, "lng": 4.0}

    }
#patch arguments are injected reverse order
@patch("producer.api_client.time.sleep", return_value=None)#mocked function returns None when called, avoid delays
@patch("producer.api_client.requests.post")  #replaces a real function with a fake one during the test, takes string path
def test_success(mock_post, mock_sleep, corridor):    #mock_post is a MagicMock object
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "routes": [{"duration": "1200s"}]
    }

    result = get_travel_time(corridor)

    assert result["status"] == "ok"
    assert result["ETA"] == 1200
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 1


@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_no_routes_dlq(mock_post, mock_sleep, corridor):

    # Fake API response with empty routes
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "routes": []
    }

    result = get_travel_time(corridor)

    assert result["status"] == "dlq"
    assert result["reason"] == "NO_ROUTES"
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 1

@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_parsing_error_dlq(mock_post, mock_sleep, corridor):

    # Fake API response with empty routes
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "routes": [{"duration":"abc"}]
    }

    result = get_travel_time(corridor)

    assert result["status"] == "dlq"
    assert result["reason"] == "PARSING_ERROR"
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 1

@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_invalid_json(mock_post, mock_sleep, corridor):

    # Fake API response with empty routes
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.side_effect = ValueError()   # controls what .json() raises


    result = get_travel_time(corridor)

    assert result["status"] == "failed"
    assert result["reason"] == "INVALID_JSON"
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 3
    assert mock_post.call_count == 3 




@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_retry_success(mock_post, mock_sleep, corridor):

    resp1 = requests.models.Response()    # Response object defined in requests.models
    resp1.status_code = 429 

    resp2 = requests.models.Response()     
    resp2.status_code = 429 

    resp3 = requests.models.Response()
    resp3.status_code = 200
    resp3.encoding = "utf-8" 
    resp3._content = b'{"routes":[{"duration":"1000s"}]}'  #_content is the internal attribute that .json() reads from, raw response in bytes

    mock_post.side_effect = [resp1, resp2, resp3]   #  controls what requests.post() returns

    result = get_travel_time(corridor)

    assert result["status"] == "ok"
    assert result["ETA"] == 1000
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 3
    assert mock_post.call_count == 3



@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_non_retryable_error(mock_post, mock_sleep, corridor):

    mock_post.return_value.status_code = 403

    result = get_travel_time(corridor)

    assert result["status"] == "failed"
    assert result["reason"] == "HTTP_403"
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 1

    # called once , no retries
    assert mock_post.call_count == 1


@patch("producer.api_client.time.sleep", return_value=None)
@patch("producer.api_client.requests.post")
def test_max_retries(mock_post, mock_sleep, corridor):

    resp = requests.models.Response()
    resp.status_code = 500
    
    mock_post.side_effect = [resp,resp,resp]
    result = get_travel_time(corridor)

    assert result["status"] == "failed"
    assert result["reason"] == "MAX_RETRIES"
    assert result["route_id"] == "test"
    assert result["charged_attempts"] == 3

    # 3 retries
    assert mock_post.call_count == 3
    