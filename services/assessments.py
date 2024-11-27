import json
import logging
import os

from services.google_drive_helpers import GoogleDrive

logger = logging.getLogger(__name__)


def assessment_one(google_drive: GoogleDrive, file_id: str) -> None:
    """
    Assessment one: Write a script to generate a report that shows the number of files and folders in total at the root
    of the source folder.
    :param file_id: the source file id we're running against
    :param google_drive: Google Drive resource
    :return:
    """
    file_data = google_drive.get_files_and_folders(file_id)

    report_data = {
        "num_folders": len(file_data["folders"]),
        "num_files": len(file_data["files"]),
        "total_objects": file_data["local_object_count"],
    }

    print(f"number folders {report_data['num_folders']}")
    print(f"number files {report_data['num_files']}")
    print(
        f"total objects in {file_data["folder_id"]}: {report_data['total_objects']}"
    )

    with open("reports/assessment_1_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=4)


def assessment_two(google_drive: GoogleDrive, file_id: str) -> None:
    """
    Assessment two: Write a script to generate a report that shows the number of child objects (recursively) for each
    top-level folder under the source folder id and a total of nested folders for the source folder.
    :param file_id: the source file id we're running against
    :param google_drive: Google Drive resource
    :return:
    """
    drive_data, total_folder_count, total_files = google_drive.get_nested_objects(file_id)

    report_data = {
        "total_nested_files": total_files,
        "total_nested_folders": total_folder_count,
        "nested_object_counts_by_folder": {},
        "total_nested_object_count": total_files + total_folder_count
    }

    print(
        f"total number of nested folders for source {file_id}: {total_folder_count}\n"
    )

    for folder in drive_data["folders"]:
        report_data["nested_object_counts_by_folder"][folder['folder_name']] = folder['nested_object_count']
        print(
            f"total child nested count for top level folder {folder['folder_name']}: {folder['nested_object_count']}"
        )

    with open("drive_data.json", "w", encoding="utf-8") as f:
        json.dump(
            drive_data, f, ensure_ascii=False, indent=4
        )

    with open("reports/assessment_2_report.json", "w", encoding="utf-8") as f:
        json.dump(
            report_data, f, ensure_ascii=False, indent=4
        )


def assessment_three(google_drive: GoogleDrive, file_id: str) -> None:
    """
    Write a script to copy the content (nested files/folders) of the source folder to the destination folder.
    :param file_id: the source file id we're running against
    :param google_drive: Google Drive resource
    :return:
    """
    source_data = {}
    pull_data = True
    if os.path.exists("drive_data.json"):
        with open("drive_data.json", "r") as f:
            source_data = json.load(f)
            if source_data["folder_id"] == file_id:
                pull_data = False

    if pull_data:
        source_data, _, _ = google_drive.get_nested_objects(file_id)

    copy_source_id = google_drive.copy_nested_items(source_data)

    print(f"copy source folder id: {copy_source_id}")

    report_data = {
        "copy_source_id": copy_source_id
    }

    with open("reports/assessment_3_report.json", "w", encoding="utf-8") as f:
        json.dump(
            report_data, f, ensure_ascii=False, indent=4
        )

