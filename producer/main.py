#runs constantly , checks hour, int hour 
#keep last_polled dict 
#keep track of total number of calls today , refresh 
#no need of ThreadPoolExecutor as of now 


from producer.corridors import CORRIDORS
from producer.scheduler import get_poll_interval, should_fetch_baseline, should_poll_corridor
from producer.api_client import get_travel_time
from producer.kafka_publisher import publish_event, publish_to_dlq, close
from datetime import datetime, timezone
import logging, json , time


#LOGGING 

#global rules for logs, threshold is INFO level and above

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s") 
log = logging.getLogger(__name__)



#STATE---------------------------------------------------------

calls_today = 0
baseline_done = False
baseline_cache = {} # today
baseline_backup = {} # fallback from file 
last_polled = {}
last_reset_day = datetime.now().date()


def midnight_reset(today):
     
     global calls_today,baseline_done, baseline_cache,last_polled, last_reset_day
     calls_today = 0
     baseline_done = False
     baseline_cache = {} # today
     #baseline_backup = {} #loses purpose if reset , don't
     last_polled = {}
     last_reset_day = today
     log.info(f"MIDNIGHT RESET COMPLETE AT {datetime.now()}")


#STORAGE FOR BASELINE TIME (FALLBACK)----------------

BASELINE_FILE = "baseline_backup.json"

def load_baseline():
    try:
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log.info("No baseline file found, starting fresh")
        return {}       
    except Exception as e:
            log.error(f"Baseline Loading Issue:{type(e).__name__}: {e}")
            return {}


def save_baseline(data:dict):
    try:
        with open(BASELINE_FILE, 'w')as f:
            json.dump(data, f)
    except Exception as e:
         log.error(f"Baseline save failed: {type(e).__name__}: {e}")
    




def fetch_baseline():
    global calls_today, baseline_done, baseline_cache, baseline_backup
    log.info("Fetching Baselines.....")

    for corridor in CORRIDORS:
        route_id = corridor["route_id"]
        
        baseline_time = get_travel_time(corridor)
        charged_calls = baseline_time.get("charged_attempts",0)
        calls_today += charged_calls

        if baseline_time["status"] == "ok":
                baseline_cache[route_id] = baseline_time["ETA"]
                baseline_backup[route_id] = baseline_time["ETA"]
                #save_baseline(baseline_backup)

                log.info(f"[BASELINE OK] {route_id} : {baseline_time['ETA']}s")

                # publish_event(route_id,baseline_time)   #NOT publishing baseline time to Kafka, not keeping track in last_polled either
        elif baseline_time["status"] =="dlq":              #not going to cache 
                success = publish_to_dlq(baseline_time)
                if success:
                     log.info(f"[BASELINE TIME DLQ PUBLISHED] {route_id} : {baseline_time['reason']}")
                if not success:
                     log.error(f"DLQ BASELINE PUBLISH FAILED {route_id} : {baseline_time['reason']}")
                #log.warning(f"[BASELINE DLQ] {route_id} : {baseline_time['reason']}")
        else: 
            #baseline_done = False #Pipeline still goes on , fallback available for baselines
            log.warning(f"[BASELINE FAILED] {route_id} : {baseline_time['reason']}")

    save_baseline(baseline_backup)
    baseline_done = True
    log.info(f"Baseline complete: {len(baseline_cache)}/{len(CORRIDORS)}")



def poll_corridors(interval:int | None):           #None -> Blackout times
    global calls_today
    #log.info("Fetching corridor ETAs......")

    for corridor in CORRIDORS:
        route_id = corridor["route_id"]

        if not should_poll_corridor(route_id,interval,last_polled):
             continue
        
        result = get_travel_time(corridor)
        charged_calls = result.get("charged_attempts",0)   #preventing TypeError
        calls_today += charged_calls
        

        if result["status"] == "ok":
                base = baseline_cache.get(route_id) or baseline_backup.get(route_id)
                payload = {"route_id": route_id,
                           "live_seconds": result["ETA"],
                           "timestamp": datetime.now(timezone.utc).isoformat()}
                if base and base >0:
                       payload["base_time_seconds"] = base
                       payload["ratio"] = round(result["ETA"]/base,3)
                       log.info(f"[LIVE] {route_id} , live={result['ETA']}s , "
                                f"base={base}s , ratio={payload['ratio']} , "
                                f"calls={calls_today}")

                else:
                       log.warning(f"[INVALID BASELINE] {route_id} : base ={base}")
                       log.info(f"[LIVE] {route_id} ,live={result['ETA']}s" )
                       payload["base_time_seconds"] = None                                 #if live values come in with no backup baseline at all, could backfill
                       payload["ratio"] = None                                             #Always ingest anyways, doesnt block pipeline , or waste api calls
                       

                success = publish_event(route_id,payload)
                if success:
                     last_polled[route_id] = datetime.now()
                     log.info(f"[LIVE TIME OK] {route_id} : {result['ETA']}s [AT] {interval}min")
                else:
                      log.error(f"Kafka publish failed: {route_id}: {result['ETA']}s ")
        
        elif result["status"] == "dlq":
                success_dlq = publish_to_dlq(result)
                if success_dlq:
                     log.info(f"[LIVE TIME DLQ] {route_id} : {result['reason']}s [AT] {interval}min")
                if not success_dlq:
                     log.error(f"DLQ PUBLISH FAILED {route_id}")

                last_polled[route_id] = datetime.now()                  #updating regardless here 
               
        else: 
           
            log.warning(f"[LIVE TIME FAILED] {route_id} : {result['reason']}")
            # do NOT update last_polled, will retry for same corridor next cycle, 



#---main loop-----------------
#Runs every 60s ,,

def run_pipeline():
    global baseline_backup
    log.info(f"Starting Pipeline....... at {datetime.now()}")
    baseline_backup = load_baseline()
    try:
        while True:
            now = datetime.now()
            hour = now.hour
            today = now.date()
            

            if last_reset_day !=today:
                midnight_reset(today)
            
            if should_fetch_baseline(hour,baseline_done):
                 fetch_baseline()

            interval = get_poll_interval(hour,calls_today)
            if interval is not None:             #not blackout time
                 poll_corridors(interval)
                 log.info(f"[HEARTBEAT] calls_today : {calls_today}")
            else:
                 log.info("Skipping -- blackout or budget reached")
            

            time.sleep(60)


    except KeyboardInterrupt :
         log.info(f"Shutting down ...")
         close()
    except Exception as e:
         log.error(f"Crash :{type(e).__name__}: {e} ")
         close()
         raise   

if __name__ == "__main__":                         #run the pipeline only when the module is run directly 
     run_pipeline()
