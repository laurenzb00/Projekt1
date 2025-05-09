class InverterReader:
    def __init__(self, api_url):
        self.api_url = api_url

    def read_data(self):
        import requests
        try:
            response = requests.get(self.api_url)
            response.raise_for_status()
            return self.parse_data(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error reading data from inverter: {e}")
            return None

    def parse_data(self, data):
        # Assuming the data contains a 'data' field with relevant information
        if 'data' in data:
            return data['data']
        else:
            print("No data found in the response.")
            return None