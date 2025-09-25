import easyocr
import re
from typing import Tuple

reader = easyocr.Reader(['en'], gpu=False)

# Returns (success, found_fields)
def extract_fields_from_image(image_path: str) -> Tuple[bool, dict]:
    result = reader.readtext(image_path, detail=0)
    text = ' '.join(result)
    found = {
        'Installation ID': None,
        'Version': None,
        'Sign Out': False
    }
    for line in result:
        if 'installation id' in line.lower():
            found['Installation ID'] = line
        if 'version' in line.lower():
            found['Version'] = line
        if 'sign out' in line.lower():
            found['Sign Out'] = True
    success = all([found['Installation ID'], found['Version'], found['Sign Out']])
    return success, found
