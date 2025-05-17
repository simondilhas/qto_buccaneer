# Project Viewer Streamlit App

A password-protected Streamlit application for viewing projects, their associated graphs, and check files.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the requirements:
```bash
pip install -r requirements.txt
```

3. Configure the password:
   - Open `.streamlit/secrets.toml`
   - Change the `password` value to your desired password

## Running the App

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Enter the password you configured in the secrets file

4. Input the paths to your:
   - Project folder
   - Project graph folder
   - Check folder

## Features

- Password protection
- Grid view of all projects with preview images
- Individual project pages with tabs for:
  - Graphs
  - Project files
  - Check files
- Responsive layout 