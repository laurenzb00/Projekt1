import logging
from fronius.inverter_reader import InverterReader
from config.settings import API_ENDPOINT

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting Fronius inverter data reader...")

    # Initialize the inverter reader
    inverter_reader = InverterReader(API_ENDPOINT)

    try:
        # Read data from the inverter
        data = inverter_reader.read_data()
        logger.info("Data retrieved from inverter: %s", data)

        # Parse the data
        parsed_data = inverter_reader.parse_data(data)
        logger.info("Parsed data: %s", parsed_data)

    except Exception as e:
        logger.error("An error occurred: %s", e)

if __name__ == "__main__":
    main()