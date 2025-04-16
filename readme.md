# Redcap Participant Selection Script

## Setup Instructions
1. Clone repository
```
git clone https://github.com/tevinpark/LLM_BJT_ENV.git
```
2. Add your `.env` file to the project folder  
   This file should contain the following environment variables:

   ```env
   REDCAP_API_TOKEN=your_redcap_api_token
   GOOGLE_SHEET_NAME=Your Google Sheet Name
   GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}  # One-line JSON string with \\n escapes
3. Install Conda (if you haven't already)
4. Create Conda environment
```
conda env create -f environment.yml
```
5. Activate Conda environment
```
conda activate redcap_env
```
6. Run the application
```
python run.py
```