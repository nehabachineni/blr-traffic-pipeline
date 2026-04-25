'''

All time-window and budget logic lives here. main.py asks the scheduler what to do. 
The scheduler decides.


# Windows: # MORNING_PEAK 07:00-11:00 30 min interval 
# # MIDDAY 11:00-16:00 60 min interval 
# # EVENING_PEAK 16:00-23:00 30 min interval 
# # BLACKOUT 23:00-07:00 no polling # # Budget: 
# # Pro SKU free tier: 5,000 calls/month 
# # Daily target: 135 calls 
# # Hard cap: 160 calls (safety margin)


'''



from datetime import datetime, timedelta

def get_window(hour:int)->str:
    if 7 <= hour < 11:
        return "MORNING PEAK"
    if 11 <= hour < 16:
        return "MIDDAY"
    if 16 <= hour < 23:
        return "EVENING PEAK"
    else:
        return "BLACKOUT"
    
FREQUENCY = {
    "MORNING PEAK" : 30,
    "MIDDAY"       : 60,
    "EVENING PEAK" : 30,
    "BLACKOUT"     : None

}
'''
    after how many minutes to poll again, takes api cost budget into account
    calls_today handled in main.py
    Returns None if pipeline should not poll.
'''
def get_poll_interval(hour:int, calls_today:int) ->int | None:

    if calls_today + 5 >= 160:    #hard cut off , +5 accounting for next cycle counts ( 5 routes )
        return None

    window = get_window(hour)
    base = FREQUENCY[window]

    if base is None:
        return None
    
   
    if calls_today >= 120:        #cut off, polls at 60 min irrespective of hour window
        return base * 2
    else:
        return base
    
    
'''
    everyday 6 am basline traffic unaware ETA is polled, reset() logic in main.py
'''
def should_fetch_baseline(hour: int, baseline_done: bool) -> bool:
    return hour == 6 and not baseline_done

'''

    last_polled is a dictionary from main.py,
    interval derived from calling get_poll_interval func

'''

def should_poll_corridor(route_id:str,interval:int,last_polled:dict )->bool:

    if route_id not in last_polled :
        return True                     # first time polling for the route
    
    elapsed_time = datetime.now() - last_polled[route_id]

    if elapsed_time >= timedelta(minutes=interval):        
        return True
    else:
        return False                     # dont poll before interval time is up 
    

def get_budget_status(calls_today: int) -> dict:
    """
    Returns current API budget status for monitoring/logging.
    """

    HARD_CAP = 160
    EMERGENCY_THRESHOLD = 120

    calls_remaining = HARD_CAP - calls_today
    monthly_projection = calls_today * 30
    within_free_tier = monthly_projection <= 5000

    if calls_today >= EMERGENCY_THRESHOLD:
        mode = "EMERGENCY"
    else:
        mode = "NORMAL"

    return {
        "calls_today": calls_today,
        "calls_remaining": calls_remaining,
        "monthly_projection": monthly_projection,
        "within_free_tier": within_free_tier,
        "mode": mode
    }
    


