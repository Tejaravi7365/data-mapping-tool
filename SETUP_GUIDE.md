# Quick Setup Guide - Running on Another PC

## Quick Start (Windows)

1. **Copy the project folder** to the target PC (or clone from GitHub)

2. **Open PowerShell/Command Prompt** and navigate to the project:
   ```powershell
   cd path\to\data-mapping-tool
   ```

3. **Create and activate virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Run the application:**
   ```powershell
   uvicorn app.main:app --reload
   ```

6. **Open your browser** and go to: http://127.0.0.1:8000

## Quick Start (macOS/Linux)

1. **Copy the project folder** to the target PC (or clone from GitHub)

2. **Open Terminal** and navigate to the project:
   ```bash
   cd path/to/data-mapping-tool
   ```

3. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Open your browser** and go to: http://127.0.0.1:8000

## Troubleshooting

### Python not found
- Make sure Python 3.8+ is installed
- Try `python3` instead of `python` on macOS/Linux
- Add Python to your system PATH

### Port already in use
- Change the port: `uvicorn app.main:app --reload --port 8080`
- Or stop the process using port 8000

### Module not found errors
- Make sure virtual environment is activated (you should see `(.venv)` in your prompt)
- Reinstall dependencies: `pip install -r requirements.txt`

### Cannot connect to Salesforce/Redshift
- Check your network connection
- Verify credentials are correct
- Ensure firewall allows outbound connections

## Accessing from Other Devices

To access the application from other devices on your network:

1. **Find your PC's IP address:**
   - Windows: `ipconfig` (look for IPv4 Address)
   - macOS/Linux: `ifconfig` or `ip addr`

2. **Run with host binding:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access from other device:**
   ```
   http://<your-pc-ip-address>:8000
   ```

4. **Configure firewall** to allow incoming connections on port 8000
