
import os
from dotenv import load_dotenv

load_dotenv()

# Add this right after the load_dotenv() call
print("===== Environment Variable Debugging =====")
raw_url = os.getenv("IFC_TO_JSON_API_URL")
print(f"Raw URL from env: '{raw_url}'")
print(f"Raw URL type: {type(raw_url)}")
print(f"Raw URL length: {len(raw_url) if raw_url else 0}")
print(f"Raw URL characters (as ordinals): {[ord(c) for c in raw_url] if raw_url else []}")