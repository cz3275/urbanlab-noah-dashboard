import threading
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
import json
from services.data_sync import DataSyncService

class AutoSyncManager:
    def __init__(self):
        self.config_file = Path("data/auto_sync_config.json")
        self.is_running = False
        self.sync_thread = None
        self.config = self.load_config()
    
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "enabled": False,
            "interval_hours": 24,
            "last_sync": None,
            "sync_census": True,
            "sync_pluto": False
        }
    
    def save_config(self):
        self.config_file.parent.mkdir(exist_ok=True, parents=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_config(self, enabled=None, interval_hours=None, sync_census=None, sync_pluto=None):
        if enabled is not None:
            self.config["enabled"] = enabled
        if interval_hours is not None:
            self.config["interval_hours"] = interval_hours
        if sync_census is not None:
            self.config["sync_census"] = sync_census
        if sync_pluto is not None:
            self.config["sync_pluto"] = sync_pluto
        self.save_config()
    
    def should_sync(self):
        if not self.config["enabled"]:
            return False
        
        if self.config["last_sync"] is None:
            return True
        
        last_sync = datetime.fromisoformat(self.config["last_sync"])
        interval = timedelta(hours=self.config["interval_hours"])
        
        return datetime.now() - last_sync >= interval
    
    def perform_sync(self):
        try:
            sync_service = DataSyncService()
            results = {"census": None, "pluto": None, "error": None}
            
            if self.config["sync_census"]:
                try:
                    census_records = sync_service.sync_all_data()
                    results["census"] = census_records
                except Exception as e:
                    results["error"] = f"Census sync failed: {str(e)}"
            
            if self.config["sync_pluto"]:
                try:
                    pluto_records = sync_service.sync_pluto_data()
                    results["pluto"] = pluto_records
                except Exception as e:
                    error_msg = f"PLUTO sync failed: {str(e)}"
                    if results["error"]:
                        results["error"] += "; " + error_msg
                    else:
                        results["error"] = error_msg
            
            self.config["last_sync"] = datetime.now().isoformat()
            self.save_config()
            
            return results
        
        except Exception as e:
            return {"census": None, "pluto": None, "error": str(e)}
    
    def check_and_sync(self):
        if self.should_sync():
            return self.perform_sync()
        return None
    
    def run_scheduler(self):
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)
    
    def start_auto_sync(self):
        if self.is_running:
            return False
        
        schedule.clear()
        interval = self.config["interval_hours"]
        schedule.every(interval).hours.do(self.perform_sync)
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.sync_thread.start()
        
        return True
    
    def stop_auto_sync(self):
        self.is_running = False
        schedule.clear()
        if self.sync_thread:
            self.sync_thread = None
    
    def get_next_sync_time(self):
        if not self.config["enabled"] or self.config["last_sync"] is None:
            return None
        
        last_sync = datetime.fromisoformat(self.config["last_sync"])
        interval = timedelta(hours=self.config["interval_hours"])
        next_sync = last_sync + interval
        
        return next_sync
    
    def get_status(self):
        status = {
            "enabled": self.config["enabled"],
            "interval_hours": self.config["interval_hours"],
            "last_sync": self.config["last_sync"],
            "sync_census": self.config["sync_census"],
            "sync_pluto": self.config["sync_pluto"],
            "next_sync": None,
            "time_until_sync": None
        }
        
        next_sync = self.get_next_sync_time()
        if next_sync:
            status["next_sync"] = next_sync.isoformat()
            time_until = next_sync - datetime.now()
            if time_until.total_seconds() > 0:
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)
                status["time_until_sync"] = f"{hours}h {minutes}m"
            else:
                status["time_until_sync"] = "Overdue"
        
        return status

