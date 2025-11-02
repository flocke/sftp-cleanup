import argparse
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from stat import S_ISDIR

import paramiko
from croniter import croniter

from config import SftpCleanupConfig as config_store

###############################################################################
# Function implementation
###############################################################################


@dataclass
class FileInfo:
    path: str
    folder: str
    sftp_attr: paramiko.SFTPAttributes
    time: datetime | None = field(init=False)

    def __post_init__(self):
        if config_store.time_method == "regex":
            if match := config_store.time_regex.search(self.sftp_attr.filename):
                self.time = datetime.strptime(
                    match.group(1), config_store.time_parse_str
                )
            else:
                self.time = None
        elif config_store.time_method == "mtime":
            self.time = datetime.fromtimestamp(self.sftp_attr.st_mtime, timezone.utc)
        else:
            self.time = None


def collect_files(sftp_client: paramiko.SFTPClient, path: str) -> list[FileInfo]:
    file_list = []

    for entry in sftp_client.listdir_attr(path):
        full_path = f"{path}/{entry.filename}"

        if S_ISDIR(entry.st_mode):
            file_list.extend(collect_files(sftp_client, full_path))
        else:
            file_list.append(FileInfo(full_path, path, entry))

    return file_list


def print_msg(msg: str, level: str = "INFO"):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][{level.center(7)}] {msg}")


def worker(dry_run: bool = False):
    if dry_run:
        print_msg("=> Running in dry-run mode <=")

    print_msg("Connecting to SFTP server")

    transport = paramiko.Transport((config_store.host, config_store.port))
    transport.connect(username=config_store.user, pkey=config_store.priv_key)

    sftp = paramiko.SFTPClient.from_transport(transport)

    print_msg("Collecting file information")

    try:
        file_list = collect_files(sftp, config_store.base_folder)
    except Exception:
        print_msg("Unable to collect files", level="ERROR")

        sftp.close()
        transport.close()

        exit(1)

    print_msg(f"- Found {len(file_list)} files")

    print_msg("Selecting files to be removed")

    current_time = datetime.now().astimezone()
    files_to_delete = []

    for f in file_list:
        if f.time:
            if current_time - f.time > config_store.retention_time:
                files_to_delete.append(f)
        else:
            print_msg(f" - No time found for file: {f.path}", level="WARN")

    print_msg(f"- Selected {len(files_to_delete)} files to be removed")

    print_msg("Processing removals")

    folders_to_check = []

    for f in files_to_delete:
        print_msg(f"- Removing file: {f.path}")

        if not dry_run:
            try:
                sftp.remove(f.path)
            except FileNotFoundError:
                print_msg(f"- File does not exist: {f}", level="WARN")
            except IOError:
                print_msg(f"  Failed to remove: {f}", level="ERROR")

        if f.folder not in folders_to_check:
            folders_to_check.append(f.folder)

    print_msg("Checking for empty folders")

    for f in folders_to_check:
        try:
            folder_content = sftp.listdir(f)

            if not folder_content:
                print_msg(f"- Removing empty folder: {f}")
                if not dry_run:
                    sftp.rmdir(f)
        except FileNotFoundError:
            print_msg(f"- Folder does not exist: {f}", level="WARN")
        except IOError:
            print_msg(f"  Failed to remove: {f}", level="ERROR")

    print_msg("Closing SFTP connection")

    sftp.close()
    transport.close()


def next_schedule_execution(schedule):
    next_runtime = croniter(schedule, datetime.now()).get_next(datetime)
    print_msg(f"Next execution: {next_runtime}")
    return next_runtime


def sleep_till_next_min():
    t = datetime.now(timezone.utc)
    sleeptime = 60 - (t.second + t.microsecond / 1000000.0)
    time.sleep(sleeptime)


###############################################################################
# Main entrypoint
###############################################################################

parser = argparse.ArgumentParser(description="Remove old files from a SFTP server.")

parser.add_argument(
    "--scheduler",
    "-s",
    action="store_true",
    help="start scheduled execution of the cleanup according to the schedule in the config",
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="execute in dry-run mode (no modifications are made on the server)",
)

args = parser.parse_args()

if args.scheduler:
    print_msg(f"Starting scheduler ({config_store.schedule})")
    next_execution = next_schedule_execution(config_store.schedule)

    while True:
        current_minute = datetime.now().replace(second=0, microsecond=0)

        if current_minute == next_execution:
            worker(dry_run=args.dry_run)
            next_execution = next_schedule_execution(config_store.schedule)
        elif current_minute > next_execution:
            print_msg("Schedule execution missed", level="ERROR")
            next_execution = next_schedule_execution(config_store.schedule)

        sleep_till_next_min()
else:
    worker(dry_run=args.dry_run)
