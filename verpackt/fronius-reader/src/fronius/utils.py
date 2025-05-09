def format_data(data):
    # Format the data retrieved from the inverter for better readability
    formatted_data = {}
    for key, value in data.items():
        formatted_data[key] = f"{value:.2f}" if isinstance(value, (int, float)) else value
    return formatted_data

def handle_exception(e):
    # Handle exceptions that may occur during the inverter reading process
    print(f"An error occurred: {str(e)}")