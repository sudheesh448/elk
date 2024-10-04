from fastapi import FastAPI, HTTPException
import asyncio
import logging
from log_config import setup_logging  # Import the logging setup

# Set up logging
setup_logging()

# Get loggers
activity_logger = logging.getLogger('activity_logger')
error_logger = logging.getLogger('error_logger')
application_logger = logging.getLogger('application_logger')

app = FastAPI()

async def log_background():
    while True:
        # Log an activity message
        activity_logger.info("Logging activity every 5 seconds")

        # Log an application message
        application_logger.info("Background task running...")

        # For demonstration, raise an exception every 5 iterations
        try:
            # Raise a simulated exception
            application_logger.info("Root endpoint accessed")
            raise ValueError("Simulated error for demonstration.")
        except Exception as e:
            # Log the error with traceback
            error_logger.error("An error occurred in the background task", exc_info=True)
    
        await asyncio.sleep(5)  # Wait for 5 seconds

@app.on_event("startup")
async def startup_event():
    # Start the logging background task
    asyncio.create_task(log_background())

@app.get("/")
async def read_root():
    application_logger.info("Root endpoint accessed")
    return {"Hello": "World"}

@app.get("/error")
async def trigger_error():
    try:
        # Simulate an error for demonstration
        raise ValueError("This is a simulated error.")
    except Exception as e:
        error_logger.error("An error occurred", exc_info=e)  # Log the error
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/status")
async def read_status():
    application_logger.info("Status endpoint accessed")
    return {"status": "running"}
