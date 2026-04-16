# ACC Server Web Management Tool

A simple web-based management dashboard for **Assetto Corsa Competizione** servers. Monitor, configure, and manage your server from a simple browser interface.

## Features

- **Web Dashboard**: Clean, responsive interface accessible from any browser
- **Configuration Management**: Easily adjust server settings
- **Session Control**: Start, stop, and manage server sessions
- **Lightweight**: Minimal resource footprint, runs alongside your ACC server

## Installation

### Prerequisites
- Python 3.7 or higher
- An Assetto Corsa Competizione server installation
- Requirements for the code are installed: 
```bash
pip install -r requirements.txt
```

### Pull from Git
- git clone https://github.com/Bloodimooni/ACC-Server-Web-Management-Tool
- copy env.example to .env
- edit .env contents to fit your setup

### Permissions
- since the ACC server is only available on Windows as far as I know, make sure the python script can access the .exe file of the server

## Usage

### Create a local User:
```pyhton
python main.py adduser username
```

### Starting the Dashboard

Run the main application:
```bash
python main.py
```

The dashboard will be available at the configured address in your `.env` file.
Default: http://localhost:8080

### Autostarting the dashboard on startup
- Press WIN + R on your keyboard or just open up "run"
- type shell:startup
- create a shortcut for "start_dashboard.vbs" in the startup folder

The dashboard will now autostart when windows boots. 


### Managing Your Server

Once logged in, you can:
- Configure race settings (track, weather, car classes, etc.)
- Manage server parameters and restrictions
- Monitor active sessions using the Console output
- Restart or shutdown the server

## Configuration

Edit the `.env` file to customize:
- Server connection details
- Web dashboard port
- API endpoints
- Setup OAuth + PKCE provider for login

Refer to `.env.example` for all available configuration options.

## Structure

```
ACC-Server-Web-Management-Tool/
├── app/                      # Backend application logic
├── frontend/                 # Web UI components
├── main.py                   
├── requirements.txt          
├── .env.example              
└── README.md                 
```


## Troubleshooting

**Dashboard won't start:**
- Verify Python version is 3.7 or higher: `python --version`
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Ensure the configured port is not already in use

**Can't connect to ACC server:**
- Verify ACC server is running
- Check `.env` configuration matches your server details
- Ensure network connectivity between dashboard and server machines

## Contributing

Found a bug or have a feature request? Feel free to open an issue!




