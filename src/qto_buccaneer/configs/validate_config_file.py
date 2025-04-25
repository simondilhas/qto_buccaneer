import sys
from pathlib import Path
import yaml
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.config_loader import validate_config, load_config

config = load_config("src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml")

def main():
    try:
        # Load config
        config = load_config("src/qto_buccaneer/configs/metrics_config_abstractBIM.yaml")
        
        # Validate config
        is_valid, messages = validate_config(config)
        
        # Print all validation messages
        print("\nConfiguration Validation Results:")
        print("================================")
        for message in messages:
            print(message)
        
        # Print final result
        print("\nFinal Result:")
        if is_valid:
            print("✓ Configuration is valid!")
        else:
            print("❌ Configuration has errors!")
            
    except Exception as e:
        print(f"\nValidation Error:")
        print(f"❌ {str(e)}")

if __name__ == "__main__":
    main()