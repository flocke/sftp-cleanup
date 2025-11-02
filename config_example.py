import paramiko
import re
from datetime import timedelta

###############################################################################
# Configuration
###############################################################################

# This is an example configuration, create a copy with the name 'config.py' and
# adapt the entries below to your needs.

class SftpCleanupConfig:
    ### SFTP connection
    host = "sftp.example.com"
    port = 22
    user = "username"
    # https://docs.paramiko.org/en/stable/api/keys.html
    priv_key = paramiko.Ed25519Key(filename="/home/USERNAME/.ssh/id_ed25519")
    #priv_key = paramiko.RSAKey(filename="/home/USERNAME/.ssh/id_rsa")
    
    base_folder = "/path/to/clean"

    ### Scheduler
    # Cron expression for scheduling (with the --scheduler flag)
    schedule = "0 0 * * *"

    ### Retention policy
    # Method to determine a files age
    #  The following options are supported:
    #  - mtime (use the mtime attribute)
    #  - regex (use a regex to extract a timestamp from the filename)
    time_method = "mtime"

    # Regex used for extracting the time from the filename (if method is 'regex')
    #  Needs to be a compiled Python regex object with one group for the time
    #  https://docs.python.org/3/library/re.html
    time_regex = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}[\+\-]\d{4})")

    # Format string used for parsing the extracted time (if method is 'regex')
    #  Needs to be a format string for strptime
    #  https://docs.python.org/3/library/datetime.html#format-codes
    time_parse_str = "%Y-%m-%d_%H-%M-%S%z"

    # Retention time (delete files older than this)
    #  Needs to be a Python timedelta object
    #  https://docs.python.org/3/library/datetime.html#timedelta-objects
    retention_time = timedelta(days=14)