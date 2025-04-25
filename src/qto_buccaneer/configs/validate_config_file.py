import sys
from pathlib import Path
import yaml
import os
from typing import Tuple, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qto_buccaneer.utils.config_loader import load_config, validate_top_level_structure

def validate_config(config: dict) -> Tuple[bool, List[str]]:
    """
    Validate the configuration file.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, validation_messages)
    """
    messages = []
    is_valid = True
    
    try:
        # Validate top-level structure
        validate_top_level_structure(config)
        messages.append("✓ Top-level structure is valid")
    except ValueError as e:
        is_valid = False
        messages.append(f"❌ {str(e)}")
    
    return is_valid, messages

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