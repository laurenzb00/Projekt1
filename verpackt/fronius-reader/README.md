# Fronius Reader

This project is designed to read data from a Fronius Gen 24 inverter using a Raspberry Pi. It provides a simple interface to interact with the inverter's API and retrieve relevant data for monitoring and analysis.

## Project Structure

```
fronius-reader
├── src
│   ├── main.py               # Entry point of the application
│   ├── fronius
│   │   ├── __init__.py       # Marks the directory as a Python package
│   │   ├── inverter_reader.py # Contains the InverterReader class for API interaction
│   │   └── utils.py          # Utility functions for data handling
│   └── config
│       └── settings.py       # Configuration settings for the application
├── requirements.txt          # Lists the project dependencies
├── README.md                 # Documentation for the project
└── .gitignore                # Specifies files to ignore in version control
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fronius-reader
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:
```
python src/main.py
```

This will initialize the application and start reading data from the Fronius inverter.

## Configuration

You can modify the configuration settings in `src/config/settings.py` to adjust API endpoints, timeout settings, and other constants as needed.

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.