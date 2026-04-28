
import requests, os, time
import requests.exceptions
from dotenv import load_dotenv


load_dotenv(".env")
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

url = "https://routes.googleapis.com/directions/v2:computeRoutes"

def build_body(corridor:dict)->dict:

    origin = corridor["origin"]
    destination = corridor["destination"]

    return {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin["lat"],
                    "longitude": origin["lng"]
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination["lat"],
                    "longitude": destination["lng"]
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }


def parse_response(raw:dict)->dict:      #assumes received valid JSON

    if "routes" not in raw or not raw["routes"] :
        return{
            "status":"dlq",
            "reason": "NO_ROUTES"
        }

    route = raw["routes"][0]
    ETA = route.get('duration')
    if not ETA:
        return{
             "status":"dlq",
             "reason": "NO_ETA"
        }
    
    try:
        ETA_seconds = int(ETA.replace("s","").strip())
    
    except Exception:
        return{
             "status":"dlq",
             "reason": "PARSING_ERROR"
        }
    
    return{

        "status":"ok",
        "ETA":ETA_seconds
    }

'''
    Retry logic:
    - Retries up to 3 times per request
    - Retries on HTTP 429/500/503 using exponential backoff
    - Retries on network failures (Timeout, ConnectionError)
    - Stops immediately on fatal HTTP errors ( 400/401/403)
    - Uses try/except for network-level failures and status codes for API-level failures

'''

def get_travel_time(corridor:dict)->dict:

  headers = {
      
          "Content-Type": "application/json",
          "X-Goog-Api-Key": API_KEY,
          "X-Goog-FieldMask": "routes.duration"

         }
  
  body = build_body(corridor)

  for attempt in range(3):
      try:
          response = requests.post(        
              url,
              json = body,
              headers = headers,
              timeout =10               #wait time atmost 10s for the API to respond, 
                                        #handle with exception ( timeout and connection errors)
          )

          if response.status_code == 200:
              try:
                raw = response.json()                #exception handling if response is not json, can raise ValueError
                data = parse_response(raw)           # here, raw is already a valid dict
                data["route_id"] = corridor["route_id"]
                return data
              except ValueError:
                   if attempt < 2:
                    time.sleep(30 * (2 ** attempt))
                    continue
                   return {
                            "status": "failed",
                            "reason": "INVALID_JSON",
                            "route_id": corridor["route_id"]
                        }
                
          if response.status_code in [429, 500,503]:            #rate limit,server down, temp down
              time.sleep(30 * (2 ** attempt))                   #back off exponentially
              continue
          
          return {                                             
              "status": "failed",
              "reason": f"HTTP_{response.status_code}",
              "route_id": corridor["route_id"]

          }
    
      except (requests.exceptions.Timeout ,requests.exceptions.ConnectionError) as e:
          if attempt < 2:    #retry only if another attempt is left, 
              time.sleep(30 * ( 2 ** attempt))
              continue
          return{
              "status":"failed",
              "reason": type(e).__name__.upper(),          #every exception is a class in python, __name__ built in attribute
              "route_id": corridor["route_id"]
          }
      
      
      except Exception as e:
          return{
              "status":"failed",
              "reason":f"UNEXPECTED_{str(e)}",
              "route_id": corridor["route_id"]
              
          }
  return {
      
      "status":"failed",
      "reason":"MAX_RETRIES",
      "route_id": corridor["route_id"]
  }