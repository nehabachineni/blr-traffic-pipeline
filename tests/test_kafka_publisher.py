from unittest.mock import patch
from producer.kafka_publisher import publish_to_dlq, publish_event
import pytest
from datetime import datetime, timezone


@patch("producer.kafka_publisher._get_producer") #patch private via string, injects mock object into  test function as an argument
def test_publish_event_success(mock_get_producer):
     '''
     
     mock_get_producer.return_value = mock_producer    # _get_producer() :producer
     mock_producer.send.return_value = mock_future     # producer.send() : future
     mock_future.get.return_value = None               # future.get() : None
     
     '''
     mock_get_producer.return_value.send.return_value.get.return_value = None

     result = publish_event("test",{"status": "ok", "ETA": 1200, "route_id": "test"})

     assert result is True

     mock_get_producer.return_value.send.assert_called_with(
        "traffic.raw.events", 
        key="test",
        value={"status": "ok", "ETA": 1200, "route_id": "test"}
    )


@patch("producer.kafka_publisher.time.sleep", return_value =None)
@patch("producer.kafka_publisher._get_producer")
def test_publish_event_failure(mock_get_producer, mock_sleep):

    mock_future = mock_get_producer.return_value.send.return_value 
    mock_future.get.side_effect = Exception("Timeout") 

    result = publish_event("test",{"status": "ok", "ETA": 1200, "route_id": "test"})

    assert result is False
    assert mock_future.get.call_count ==3
    mock_get_producer.return_value.send.assert_called_with(
        "traffic.raw.events", 
        key="test",
        value={"status": "ok", "ETA": 1200, "route_id": "test"}
    )

@patch("producer.kafka_publisher.time.sleep", return_value =None)
@patch("producer.kafka_publisher._get_producer")
def test_publish_event_retry_success(mock_get_producer,mock_sleep):

    mock_future = mock_get_producer.return_value.send.return_value 
    mock_future.get.side_effect = [Exception("fail"), None]

    result = publish_event("test",{"status": "ok", "ETA": 1200, "route_id": "test"})

    assert result is True
    assert mock_future.get.call_count == 2
    mock_get_producer.return_value.send.assert_called_with(
        "traffic.raw.events", 
        key="test",
        value={"status": "ok", "ETA": 1200, "route_id": "test"}
    )
'''
    

   Patches datetime.now to provide a deterministic timestamp, 
   preventing test failure due to execution lag between 
   the application logic and the test assertion


'''
@patch("producer.kafka_publisher.datetime")
@patch("producer.kafka_publisher._get_producer")
def test_publish_to_dlq(mock_get_producer, mock_datetime):

    fixed_now = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = fixed_now
    fixed_timestamp = fixed_now.isoformat()
    mock_get_producer.return_value.send.return_value.get.return_value = None

    result = publish_to_dlq({"status": "dlq", "reason":"NO_ROUTES", "route_id": "test"})

    assert result is True
    mock_get_producer.return_value.send.assert_called_once_with(
        "traffic.dlq", 
        key="test",
        value={"status": "dlq", "reason":"NO_ROUTES", "route_id": "test", "dlq_timestamp": fixed_timestamp}
    )
