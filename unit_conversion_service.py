"""
Universal Unit Conversion Microservice
A simple HTTP-based microservice for converting between various units.

Usage:
    python unit_conversion_service.py [port]
    
Default port: 6001

Endpoints:
    GET /convert?value=X&from=UNIT&to=UNIT  - Convert between units
    GET /units                               - List all supported units
    GET /healthz                             - Health check
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Unit Conversion Microservice", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== CONVERSION FORMULAS ====================

class UnitConverter:
    """Handles all unit conversions."""
    
    # Temperature conversions (to Celsius as base)
    TEMP_TO_CELSIUS = {
        'celsius': lambda x: x,
        'c': lambda x: x,
        'fahrenheit': lambda x: (x - 32) * 5/9,
        'f': lambda x: (x - 32) * 5/9,
        'kelvin': lambda x: x - 273.15,
        'k': lambda x: x - 273.15,
    }
    
    # Temperature conversions (from Celsius)
    TEMP_FROM_CELSIUS = {
        'celsius': lambda x: x,
        'c': lambda x: x,
        'fahrenheit': lambda x: (x * 9/5) + 32,
        'f': lambda x: (x * 9/5) + 32,
        'kelvin': lambda x: x + 273.15,
        'k': lambda x: x + 273.15,
    }
    
    # Distance conversions (to meters as base)
    DIST_TO_METERS = {
        'meters': lambda x: x,
        'm': lambda x: x,
        'kilometers': lambda x: x * 1000,
        'km': lambda x: x * 1000,
        'miles': lambda x: x * 1609.344,
        'mi': lambda x: x * 1609.344,
        'feet': lambda x: x * 0.3048,
        'ft': lambda x: x * 0.3048,
        'inches': lambda x: x * 0.0254,
        'in': lambda x: x * 0.0254,
        'centimeters': lambda x: x * 0.01,
        'cm': lambda x: x * 0.01,
    }
    
    # Distance conversions (from meters)
    DIST_FROM_METERS = {
        'meters': lambda x: x,
        'm': lambda x: x,
        'kilometers': lambda x: x / 1000,
        'km': lambda x: x / 1000,
        'miles': lambda x: x / 1609.344,
        'mi': lambda x: x / 1609.344,
        'feet': lambda x: x / 0.3048,
        'ft': lambda x: x / 0.3048,
        'inches': lambda x: x / 0.0254,
        'in': lambda x: x / 0.0254,
        'centimeters': lambda x: x / 0.01,
        'cm': lambda x: x / 0.01,
    }
    
    # Speed conversions (to m/s as base)
    SPEED_TO_MS = {
        'meters_per_second': lambda x: x,
        'mps': lambda x: x,
        'kilometers_per_hour': lambda x: x / 3.6,
        'kph': lambda x: x / 3.6,
        'kmh': lambda x: x / 3.6,
        'miles_per_hour': lambda x: x * 0.44704,
        'mph': lambda x: x * 0.44704,
        'knots': lambda x: x * 0.514444,
        'kt': lambda x: x * 0.514444,
    }
    
    # Speed conversions (from m/s)
    SPEED_FROM_MS = {
        'meters_per_second': lambda x: x,
        'mps': lambda x: x,
        'kilometers_per_hour': lambda x: x * 3.6,
        'kph': lambda x: x * 3.6,
        'kmh': lambda x: x * 3.6,
        'miles_per_hour': lambda x: x / 0.44704,
        'mph': lambda x: x / 0.44704,
        'knots': lambda x: x / 0.514444,
        'kt': lambda x: x / 0.514444,
    }
    
    # Pressure conversions (to hPa as base)
    PRESSURE_TO_HPA = {
        'hectopascals': lambda x: x,
        'hpa': lambda x: x,
        'millibars': lambda x: x,
        'mbar': lambda x: x,
        'inches_mercury': lambda x: x * 33.8639,
        'inhg': lambda x: x * 33.8639,
        'millimeters_mercury': lambda x: x * 1.33322,
        'mmhg': lambda x: x * 1.33322,
        'pascals': lambda x: x / 100,
        'pa': lambda x: x / 100,
    }
    
    # Pressure conversions (from hPa)
    PRESSURE_FROM_HPA = {
        'hectopascals': lambda x: x,
        'hpa': lambda x: x,
        'millibars': lambda x: x,
        'mbar': lambda x: x,
        'inches_mercury': lambda x: x / 33.8639,
        'inhg': lambda x: x / 33.8639,
        'millimeters_mercury': lambda x: x / 1.33322,
        'mmhg': lambda x: x / 1.33322,
        'pascals': lambda x: x * 100,
        'pa': lambda x: x * 100,
    }
    
    @staticmethod
    def get_category(unit: str) -> Optional[str]:
        """Determine which category a unit belongs to."""
        unit_lower = unit.lower()
        
        if unit_lower in UnitConverter.TEMP_TO_CELSIUS:
            return 'temperature'
        elif unit_lower in UnitConverter.DIST_TO_METERS:
            return 'distance'
        elif unit_lower in UnitConverter.SPEED_TO_MS:
            return 'speed'
        elif unit_lower in UnitConverter.PRESSURE_TO_HPA:
            return 'pressure'
        
        return None
    
    @staticmethod
    def convert(value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert a value from one unit to another.
        
        Args:
            value: The value to convert
            from_unit: Source unit (e.g., 'celsius', 'miles', 'mph')
            to_unit: Target unit (e.g., 'fahrenheit', 'kilometers', 'kph')
        
        Returns:
            Converted value
        
        Raises:
            ValueError: If units are incompatible or unknown
        """
        from_lower = from_unit.lower()
        to_lower = to_unit.lower()
        
        # Determine category
        from_category = UnitConverter.get_category(from_lower)
        to_category = UnitConverter.get_category(to_lower)
        
        if not from_category:
            raise ValueError(f"Unknown unit: {from_unit}")
        if not to_category:
            raise ValueError(f"Unknown unit: {to_unit}")
        if from_category != to_category:
            raise ValueError(f"Cannot convert {from_unit} to {to_unit} - different categories")
        
        # Perform conversion via base unit
        if from_category == 'temperature':
            base_value = UnitConverter.TEMP_TO_CELSIUS[from_lower](value)
            result = UnitConverter.TEMP_FROM_CELSIUS[to_lower](base_value)
        elif from_category == 'distance':
            base_value = UnitConverter.DIST_TO_METERS[from_lower](value)
            result = UnitConverter.DIST_FROM_METERS[to_lower](base_value)
        elif from_category == 'speed':
            base_value = UnitConverter.SPEED_TO_MS[from_lower](value)
            result = UnitConverter.SPEED_FROM_MS[to_lower](base_value)
        elif from_category == 'pressure':
            base_value = UnitConverter.PRESSURE_TO_HPA[from_lower](value)
            result = UnitConverter.PRESSURE_FROM_HPA[to_lower](base_value)
        else:
            raise ValueError(f"Unknown category: {from_category}")
        
        return result


# ==================== API ENDPOINTS ====================

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Unit Conversion Microservice",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/convert")
async def convert_units(
    value: float = Query(..., description="Value to convert"),
    from_unit: str = Query(..., alias="from", description="Source unit (e.g., celsius, miles)"),
    to_unit: str = Query(..., alias="to", description="Target unit (e.g., fahrenheit, kilometers)")
):
    """
    Convert a value from one unit to another.
    
    Examples:
        /convert?value=32&from=fahrenheit&to=celsius
        /convert?value=100&from=miles&to=kilometers
        /convert?value=60&from=mph&to=kph
    
    Returns:
        {
            "value": 32,
            "from": "fahrenheit",
            "to": "celsius",
            "result": 0.0,
            "category": "temperature"
        }
    """
    try:
        result = UnitConverter.convert(value, from_unit, to_unit)
        category = UnitConverter.get_category(from_unit.lower())
        
        logger.info(f"Conversion: {value} {from_unit} → {result:.4f} {to_unit}")
        
        return {
            "value": value,
            "from": from_unit,
            "to": to_unit,
            "result": round(result, 6),  # Round to 6 decimal places
            "category": category
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/units")
async def list_units():
    """
    List all supported units organized by category.
    
    Returns:
        {
            "categories": ["temperature", "distance", "speed", "pressure"],
            "temperature": ["celsius", "fahrenheit", "kelvin", ...],
            "distance": ["meters", "kilometers", "miles", ...],
            ...
        }
    """
    return {
        "categories": ["temperature", "distance", "speed", "pressure"],
        "temperature": list(set(UnitConverter.TEMP_TO_CELSIUS.keys())),
        "distance": list(set(UnitConverter.DIST_TO_METERS.keys())),
        "speed": list(set(UnitConverter.SPEED_TO_MS.keys())),
        "pressure": list(set(UnitConverter.PRESSURE_TO_HPA.keys()))
    }


@app.get("/batch-convert")
async def batch_convert(
    values: str = Query(..., description="Comma-separated values (e.g., '32,50,100')"),
    from_unit: str = Query(..., alias="from", description="Source unit"),
    to_unit: str = Query(..., alias="to", description="Target unit")
):
    """
    Convert multiple values at once.
    
    Example:
        /batch-convert?values=32,50,100&from=fahrenheit&to=celsius
    
    Returns:
        {
            "from": "fahrenheit",
            "to": "celsius",
            "conversions": [
                {"value": 32, "result": 0.0},
                {"value": 50, "result": 10.0},
                {"value": 100, "result": 37.78}
            ]
        }
    """
    try:
        # Parse comma-separated values
        value_list = [float(v.strip()) for v in values.split(',')]
        
        # Convert each value
        conversions = []
        for val in value_list:
            result = UnitConverter.convert(val, from_unit, to_unit)
            conversions.append({
                "value": val,
                "result": round(result, 6)
            })
        
        return {
            "from": from_unit,
            "to": to_unit,
            "count": len(conversions),
            "conversions": conversions
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch conversion failed: {str(e)}")


def main():
    """Main entry point."""
    import uvicorn
    
    port = 6001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting Unit Conversion Microservice on port {port}")
    logger.info("Supported conversions: Temperature, Distance, Speed, Pressure")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()