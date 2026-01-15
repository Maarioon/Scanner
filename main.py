"""
Vehicle Diagnostics System - OBD-II Backend Module
Python backend for connecting to vehicles and processing diagnostic data
"""

import obd
import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
from datetime import datetime

# Initialize FastAPI
app = FastAPI(title="Vehicle Diagnostics API")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Vehicle Diagnostics API is running. Use the UI to interact."}


# Enable CORS for Flutter/React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection storage
active_connections: Dict[str, obd.OBD] = {}

# ===========================
# Vehicle Data Models
# ===========================

class VehicleInfo(BaseModel):
    vin: Optional[str] = None
    protocol: Optional[str] = None
    connected: bool = False

class SensorData(BaseModel):
    timestamp: str
    rpm: Optional[float] = None
    speed: Optional[float] = None
    coolant_temp: Optional[float] = None
    engine_load: Optional[float] = None
    throttle_position: Optional[float] = None
    fuel_level: Optional[float] = None

class DiagnosticTroubleCode(BaseModel):
    code: str
    description: str
    severity: str  # "critical", "warning", "info"

# ===========================
# Vehicle OBD-II Connection Handler
# ===========================

class OBDConnection:
    def __init__(self, port: str = None):
        """Initialize OBD connection"""
        self.connection = None
        self.port = port
        self.demo_mode = False
        
    def connect(self) -> bool:
        """Connect to vehicle via OBD-II"""
        try:
            if self.port == "DEMO":
                print("Starting DEMO mode connection")
                self.demo_mode = True
                return True
                
            if self.port:
                self.connection = obd.OBD(self.port)
            else:
                # Auto-detect port
                self.connection = obd.OBD()
            
            return self.connection.is_connected()
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close OBD connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get_vehicle_info(self) -> VehicleInfo:
        """Get basic vehicle information"""
        if self.demo_mode:
            return VehicleInfo(vin="1M8GDM9A_KP042788", protocol="ISO 15765-4 CAN (11 bit ID, 500 kbaud)", connected=True)

        if not self.connection or not self.connection.is_connected():
            return VehicleInfo(connected=False)
        
        try:
            # Get VIN if supported
            vin_response = self.connection.query(obd.commands.VIN)
            vin = str(vin_response.value) if vin_response.value else None
            
            return VehicleInfo(
                vin=vin,
                protocol=self.connection.protocol_name(),
                connected=True
            )
        except Exception as e:
            print(f"Error getting vehicle info: {e}")
            return VehicleInfo(connected=True)
    
    def read_sensor_data(self) -> SensorData:
        """Read real-time sensor data from vehicle"""
        if self.demo_mode:
             import random
             return SensorData(
                 timestamp=datetime.now().isoformat(),
                 rpm=random.randint(800, 3000),
                 speed=random.randint(0, 120),
                 coolant_temp=random.randint(80, 110),
                 engine_load=random.uniform(10, 50),
                 throttle_position=random.uniform(0, 40),
                 fuel_level=random.uniform(30, 90)
             )

        if not self.connection or not self.connection.is_connected():
            raise Exception("Not connected to vehicle")
        
        data = SensorData(timestamp=datetime.now().isoformat())
        
        try:
            # Read RPM
            rpm_response = self.connection.query(obd.commands.RPM)
            if rpm_response.value:
                data.rpm = rpm_response.value.magnitude
            
            # Read Speed
            speed_response = self.connection.query(obd.commands.SPEED)
            if speed_response.value:
                data.speed = speed_response.value.magnitude
            
            # Read Coolant Temperature
            temp_response = self.connection.query(obd.commands.COOLANT_TEMP)
            if temp_response.value:
                data.coolant_temp = temp_response.value.magnitude
            
            # Read Engine Load
            load_response = self.connection.query(obd.commands.ENGINE_LOAD)
            if load_response.value:
                data.engine_load = load_response.value.magnitude
            
            # Read Throttle Position
            throttle_response = self.connection.query(obd.commands.THROTTLE_POS)
            if throttle_response.value:
                data.throttle_position = throttle_response.value.magnitude
            
            # Read Fuel Level
            fuel_response = self.connection.query(obd.commands.FUEL_LEVEL)
            if fuel_response.value:
                data.fuel_level = fuel_response.value.magnitude
                
        except Exception as e:
            print(f"Error reading sensors: {e}")
        
        return data
    
    def get_diagnostic_codes(self) -> List[DiagnosticTroubleCode]:
        """Read Diagnostic Trouble Codes (DTCs)"""
        if self.demo_mode:
            return [
                DiagnosticTroubleCode(code="P0300", description="Random/Multiple Cylinder Misfire Detected", severity="critical"),
                DiagnosticTroubleCode(code="P0171", description="System Too Lean (Bank 1)", severity="warning"),
                DiagnosticTroubleCode(code="C0035", description="Left Front Wheel Speed Sensor Supply Voltage Circuit", severity="info")
            ]

        if not self.connection or not self.connection.is_connected():
            raise Exception("Not connected to vehicle")
        
        dtc_response = self.connection.query(obd.commands.GET_DTC)
        
        if not dtc_response.value:
            return []
        
        dtcs = []
        for code, description in dtc_response.value:
            # Determine severity based on code prefix
            severity = "info"
            if code.startswith("P0"):
                severity = "critical"
            elif code.startswith("P1"):
                severity = "warning"
            elif code.startswith(("C", "B", "U")):
                severity = "warning"
            
            dtcs.append(DiagnosticTroubleCode(
                code=code,
                description=description,
                severity=severity
            ))
        
        return dtcs
    
    def clear_diagnostic_codes(self) -> bool:
        """Clear all DTCs from vehicle"""
        if not self.connection or not self.connection.is_connected():
            raise Exception("Not connected to vehicle")
        
        try:
            self.connection.query(obd.commands.CLEAR_DTC)
            return True
        except Exception as e:
            print(f"Error clearing DTCs: {e}")
            return False

# ===========================
# API Endpoints
# ===========================

@app.post("/connect")
async def connect_vehicle(port: Optional[str] = None):
    """Connect to vehicle via OBD-II"""
    connection_id = "default"
    
    obd_conn = OBDConnection(port)
    if obd_conn.connect():
        active_connections[connection_id] = obd_conn
        vehicle_info = obd_conn.get_vehicle_info()
        return {
            "status": "connected",
            "vehicle_info": vehicle_info.dict()
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to vehicle")

@app.post("/disconnect")
async def disconnect_vehicle():
    """Disconnect from vehicle"""
    connection_id = "default"
    
    if connection_id in active_connections:
        active_connections[connection_id].disconnect()
        del active_connections[connection_id]
        return {"status": "disconnected"}
    
    raise HTTPException(status_code=404, detail="No active connection")

@app.get("/vehicle/info")
async def get_vehicle_info():
    """Get vehicle information"""
    connection_id = "default"
    
    if connection_id not in active_connections:
        raise HTTPException(status_code=404, detail="Not connected to vehicle")
    
    vehicle_info = active_connections[connection_id].get_vehicle_info()
    return vehicle_info.dict()

@app.get("/sensors/live")
async def get_live_sensors():
    """Get real-time sensor data"""
    connection_id = "default"
    
    if connection_id not in active_connections:
        raise HTTPException(status_code=404, detail="Not connected to vehicle")
    
    sensor_data = active_connections[connection_id].read_sensor_data()
    return sensor_data.dict()

@app.get("/diagnostics/codes")
async def get_trouble_codes():
    """Get diagnostic trouble codes"""
    connection_id = "default"
    
    if connection_id not in active_connections:
        raise HTTPException(status_code=404, detail="Not connected to vehicle")
    
    dtcs = active_connections[connection_id].get_diagnostic_codes()
    return {"codes": [dtc.dict() for dtc in dtcs]}

@app.post("/diagnostics/clear")
async def clear_trouble_codes():
    """Clear all diagnostic trouble codes"""
    connection_id = "default"
    
    if connection_id not in active_connections:
        raise HTTPException(status_code=404, detail="Not connected to vehicle")
    
    success = active_connections[connection_id].clear_diagnostic_codes()
    return {"cleared": success}

@app.websocket("/ws/sensors")
async def websocket_sensors(websocket: WebSocket):
    """WebSocket for real-time sensor streaming"""
    await websocket.accept()
    connection_id = "default"
    
    # Demo mode simulator state
    demo_rpm = 800
    demo_speed = 0
    demo_direction = 1
    
    try:
        while True:
            if connection_id in active_connections:
                sensor_data = active_connections[connection_id].read_sensor_data()
                await websocket.send_json(sensor_data.dict())
            else:
                # DEMO MODE: Send simulated data so UI is never "dead"
                # Simulate revving engine
                demo_rpm += (100 * demo_direction)
                if demo_rpm > 3500: demo_direction = -1
                if demo_rpm < 800: demo_direction = 1
                
                demo_data = {
                    "timestamp": datetime.now().isoformat(),
                    "rpm": demo_rpm,
                    "speed": abs(demo_rpm / 40), # correlated dummy speed
                    "coolant_temp": 90,
                    "engine_load": 35.5,
                    "throttle_position": 15,
                    "fuel_level": 75,
                    "status": "DEMO_MODE"
                }
                await websocket.send_json(demo_data)
            
            await asyncio.sleep(0.1)  # Faster update rate (10Hz) for smooth gauges
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass # Already closed

# ===========================
# Run Server
# ===========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
