import os , json, logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv(".env")
log = logging.getLogger(__name__)

MAIN_TOPIC = os.getenv("KAFKA_TOPIC","traffic.raw.events")    #defaults
DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC","traffic.dlq")

#Singleton Producer

'''

    Returns a Singleton KafkaProducer instance ( represents an open connection to kafka broker)
    Creates the producer on first call and reuses it on all subsequent calls.
    Avoids the cost of opening a new TCP connection to Kafka for every message.

    Private function : call publish_event() or publish_to_dlq() instead.

    Returns:
        KafkaProducer: the shared producer instance


'''

_producer = None  #Private, global variable/ module-level


def _get_producer():     #internal implementation detail, protects singleton
    global _producer     #module level, not a new local var
    if _producer is None:
        _producer = KafkaProducer(

            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            #Kafka only speaks in bytes
            key_serializer = str.encode,                                    #optional but prevents round-robin and 
                                                                            #uses hashing for partition selection for an incoming message
                                                                            
            value_serializer = lambda v : json.dumps(v).encode("utf-8")    #converts payload dict to JSON string to bytes
                                                                            # KafkaProducer calls lambda automatically on every value

        )
    return _producer

#Main Publish

'''

    Sends a valid traffic event to the main Kafka topic.

    Called by main.py when api_client.py returns status="ok".
    Blocks until Kafka confirms receipt before returning.

    Args:
        route_id: corridor identifier used as Kafka message key
                  e.g. "diary_circle_to_jigani"
                  determines which partition the message lands in (via key hash)

        payload:  the full result dict from api_client.get_travel_time() as message value
                  e.g. {"status": "ok", "ETA": 1200, "route_id": "..."}

    Returns:
        True  if Kafka confirmed the message was received
        False if anything went wrong (network, timeout, broker down)


'''

def publish_event(route_id:str, payload:dict)->bool:

    #.send() is async, puts message in internal buffer, returns immediately, no waiting( High throughput)
    #KafkaProducer applies key_serializer and value_serializer automatically here
    #background thread picks up message sends to Kafka over TCP
    #.get() code waits here
    #Kafka broker receives message , sends acknowledgement back
    #background thread marks Future as done
    #.get() unblocks and returns
    


    try:                                                                
                                                           # _get_producer() creates (or reuses) KafkaProducer
                                                           # background thread already running from first instantiation
        future = _get_producer().send(                     #.send() returns a FutureRecordMetadata object (kafka-python library class)
                MAIN_TOPIC,
                key= route_id,
                value= payload
            ) 
        

        # .get() blocks here ,waits (for the background thread to resolve) up to 10s for Kafka to confirm receipt
        # turns the async send into synchronous so that failures are known
        # raises exception if timeout or broker error
        # .get()  is a method method of FutureRecordMetadata class
        future.get(timeout =10)                         

        return True      #Kafka confirmed, message written to partition
        

    except Exception as e:
        log.error(f"Kafka MAIN publish failed: {type(e).__name__}: {e}")
        return False



# DLQ Publish 
"""

    Sends bad/malformed data to DLQ topic.
    Adds metadata for debugging.

    Called by main.py when api_client.py returns status="dlq" with the reason.
    

"""

def publish_to_dlq(payload: dict) -> bool:
    
    route_id = payload.get("route_id", "unknown")      #could be unknown due to NO_ROUTES error 

    dlq_payload = {
        **payload,                              # spreads all of payload's key value pairs here, dict unpacking, avoids mutating og dict
        "dlq_timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        future = _get_producer().send(
            DLQ_TOPIC,
            key=route_id,
            value=dlq_payload
        )

        future.get(timeout=10)

        return True

    except Exception as e:
        log.error(f"Kafka DLQ publish failed: {type(e).__name__}: {e}")
        return False
    
#Shutdown

def close():
    global _producer

    if _producer:          #checks producer's existence first, dont call flush() on None etc
                           #.flush() and .close() are methods of KafkaProducer class
        _producer.flush()  #waits until  messages in buffer are sent and confirmed by Kafka
        _producer.close()  #closes TCP connection to the broker
        _producer = None   #Resets to initial state 


