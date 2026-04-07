import random
import uuid
import json
from datetime import datetime, timedelta
from faker import Faker
from azure.eventhub import EventHubProducerClient, EventData
import logging
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import os

# Pulling Data Generator Function
from service_cab import generate_YJ_ride_confirmation

PRIMARY_CONNECTION_STRING = os.getenv("PRIMARY_CONNECTION_STRING")
SECONDARY_CONNECTION_STRING = os.getenv("SECONDARY_CONNECTION_STRING")
EVENT_HUBNAME = os.getenv("EVENT_HUBNAME")

def send_to_event_hub(ride_data=None, batch_size=1):
    """
    Send data to Event Hub with automatic failover to secondary connection
    """
    
    # Define connection configurations
    connection_configs = [
        {
            "name": "primary",
            "connection_string": PRIMARY_CONNECTION_STRING
        },
        {
            "name": "secondary", 
            "connection_string": SECONDARY_CONNECTION_STRING
        }
    ]
    
    last_error = None
    
    # Try each connection configuration
    for config in connection_configs:
        try:
            print(f"Attempting to send using {config['name']} connection...")
            
            # Initialize Event Hub Producer Client
            producer = EventHubProducerClient.from_connection_string(
                config['connection_string'],
                eventhub_name=EVENT_HUBNAME
            )
            
            # Prepare ride records
            ride_json = json.dumps(ride_data) 
            
            # Create batch of events
            event_batch = producer.create_batch()
            
            # Create event with ride data 
            event = EventData(ride_json)
            
            # Add event to batch
            event_batch.add(event)
            
            # Send batch to Event Hub
            producer.send_batch(event_batch)
            
            producer.close()
            
            print(f"Successfully sent to Event Hub using {config['name']} connection")
            return f"Successfully sent to Event Hub using {config['name']} connection"
            
        except Exception as e:
            last_error = str(e)
            print(f"Error sending data to Event Hub using {config['name']} connection: {last_error}")
            
            # If this was the last connection attempt, log the failure
            if config == connection_configs[-1]:
                print(f"All connection attempts failed. Last error: {last_error}")
                return False
            else:
                print(f"Falling back to next connection...")
                continue

if __name__ == "__main__":
    print(f"Using Primary Connection String: {PRIMARY_CONNECTION_STRING[:50]}...")  # Only show partial for security
    print(f"Using Secondary Connection String: {SECONDARY_CONNECTION_STRING[:50]}...")  # Only show partial for security
    print(f"Using Event Hub Name: {EVENT_HUBNAME}")
    print("=" * 80)
    print("SINGLE RIDE CONFIRMATION")
    print("=" * 80)
    ride = generate_YJ_ride_confirmation()
    print(ride)
    print(json.dumps(ride, indent=2))
    
    print("\n" + "=" * 80)
    print("SENDING SINGLE RIDE TO EVENT HUB (WITH FAILOVER)")
    result = send_to_event_hub(ride)
    print(f"Result: {result}")