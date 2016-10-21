import logging
import os
from subprocess import Popen, PIPE

SOX = 'sox'

def peak_level(track_path):
    """
    Accepts a path to a sox-decodable audio file.

    Returns track peak level from sox ('maximum amplitude') as a float.
    Returns None on error.
    """
    if not os.path.exists(track_path):
        logging.warning("SoX peak detection failed: file not found")
        return None
    sox = Popen([SOX, track_path, "-n", "stat"], stderr=PIPE)
    out, err = sox.communicate()
    if sox.returncode:
        logging.warning("SoX peak detection failed: " + str(sox.returncode))
        return None
    # relevant captured line looks like:
    # Maximum amplitude: 0.123456
    return float(err.splitlines()[3].split()[2])
