import logging
import logging.config
import os
import time
import traceback
from dotenv import load_dotenv
from datetime import datetime, timezone


import socket
import json

class LogstashTCPHandler(logging.Handler):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self.connect()

    def connect(self):
        """Establishes a connection to the Logstash server."""
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                break  # Successfully connected
            except (socket.error, ConnectionRefusedError):
                logging.error("Failed to connect to Logstash. Retrying...")
                time.sleep(5)  

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.sock.sendall((log_entry + '\n').encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            logging.error("Connection lost, attempting to reconnect.")
            self.connect()  # Attempt to reconnect
            self.emit(record) 

    def close(self):
        if self.sock:
            self.sock.close()
        super().close()


# Load environment variables
load_dotenv()

# Get NODE_ID and SERVICE_ID from environment variables
NODE_ID = 1
SERVICE_ID = 50
SNOWFLAKE_INSTANCE = NODE_ID + SERVICE_ID

# Initialize Snowflake generator
# snowflake_gen = SnowflakeGenerator(SNOWFLAKE_INSTANCE)

# Define custom formatters
class CustomFormatter(logging.Formatter):
    def format(self, record):
        utc_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        formatted_time = utc_time.isoformat()
        record.snowflake_id = 1245
        return f"{record.snowflake_id}::{formatted_time}::{record.getMessage()}"

class CustomErrorFormatter(logging.Formatter):
    def format(self, record):
        # record.snowflake_id = next(snowflake_gen)
        record.machine_id = 'YOUR_MACHINE_ID_HERE'
        record.snowflake_id = 1245
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            stack_trace = ''.join(traceback.format_tb(exc_traceback))
            record.exc_type = exc_type.__name__
            record.exc_message = str(exc_value)
            record.stack_trace = stack_trace
            record.exc_info = None
        else:
            record.exc_type = ''
            record.exc_message = ''
            record.stack_trace = ''

        return (f"{record.snowflake_id}::{datetime.utcnow().isoformat()}::{record.machine_id}::{record.levelname}\n"
                f"*****\nException Type: {record.exc_type}\n"
                f"Message: {record.exc_message}\n"
                f"Location: {record.filename}:{record.lineno} {record.funcName}\n"
                f"Traceback: {record.stack_trace}\n______\n")

class CustomApplicationlogFormatter(logging.Formatter):
    def format(self, record):
        record.snowflake_id = 1245
        record.machine_id = 'YOUR_MACHINE_ID_HERE'
        return f"{record.snowflake_id}::{datetime.utcnow().isoformat()}::{record.machine_id}::{record.levelname}::{record.getMessage()}"
    

class LogstashFormatter(logging.Formatter):
    """Formatter for sending logs to Logstash in JSON format."""
    def format(self, record):
        utc_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        formatted_time = utc_time.isoformat()
        log_entry = {
            "snowflake_id": 1245,
            "@timestamp": formatted_time,
            "machine_id": 'YOUR_MACHINE_ID_HERE',
            "level": record.levelname,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }

        # Include exception details if available
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            stack_trace = ''.join(traceback.format_tb(exc_traceback))
            log_entry["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "stack_trace": stack_trace
            }

        return json.dumps(log_entry)

def setup_logging():
    # Get the directory where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Define log file paths
    error_log_path = os.path.join(base_dir, 'logs', 'error_log', 'errors.log')
    application_log_path = os.path.join(base_dir, 'logs', 'application_log', 'application.log')
    activity_log_path = os.path.join(base_dir, 'logs', 'activity_log', 'activity.log')  # Path for activity logs

    # Ensure directories exist
    os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
    os.makedirs(os.path.dirname(application_log_path), exist_ok=True)
    os.makedirs(os.path.dirname(activity_log_path), exist_ok=True)  # Ensure activity log directory exists

    # Define Logstash configuration
    logstash_host = "localhost"  # Use your Logstash host
    logstash_port = 5000       # Use port 5000 for TCP input

    logstash_handler = LogstashTCPHandler(logstash_host, logstash_port)

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'custom_formatter': {
                '()': CustomFormatter,
            },
            'error_formatter': {
                '()': CustomErrorFormatter,
            },
            'application_formatter': {
                '()': CustomApplicationlogFormatter,
            },
            'logstash': {
                '()': LogstashFormatter,  # Use the LogstashFormatter
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
            'error_file': {
                'class': 'logging.FileHandler',
                'filename': error_log_path,
                'formatter': 'error_formatter',
            },
            'application_file': {
                'class': 'logging.FileHandler',
                'filename': application_log_path,
                'formatter': 'application_formatter',
            },
            'activity_file': {  # File handler for activity logs
                'class': 'logging.FileHandler',
                'filename': activity_log_path,
                'formatter': 'custom_formatter',
            },
            'logstash': {
                '()': LogstashTCPHandler,
                'host': logstash_host,
                'port': logstash_port,
                'formatter': 'logstash',
            },
        },
        'loggers': {
            'activity_logger': {
                'handlers': ['activity_file', 'logstash'],  # Use file and Logstash handler for activity logs
                'level': 'DEBUG',
            },
            'error_logger': {
                'handlers': ['error_file', 'logstash'],  # Send errors to Logstash as well
                'level': 'WARNING',
                'propagate': False,
            },
            'application_logger': {
                'handlers': ['application_file', 'logstash'],  # Send application logs to Logstash
                'level': 'INFO',
                'propagate': True,
            },
        },
    }
    logging.config.dictConfig(logging_config)

# Set up logging

