import click
import logging
import yaml

import services.assessments as assessments
import services.google_drive_helpers as google_drive_helpers


@click.command()
@click.argument(
    "assessment", type=click.Choice(["all", "one", "two", "three"]), default="all"
)
@click.argument("file_id", type=str, default="")
def main(assessment: str, file_id: None) -> None:
    # load config
    config = yaml.safe_load(open("config.yaml"))
    if not file_id:
        file_id = config["parent_file_id"]

    # get credentials and instantiate Google Drive connection and object
    credentials = google_drive_helpers.get_credentials()
    if not credentials:
        return
    google_drive = google_drive_helpers.GoogleDrive(credentials, config)

    # run assessments
    match assessment:
        case "one":
            assessments.assessment_one(google_drive, file_id)
        case "two":
            assessments.assessment_two(google_drive, file_id)
        case "three":
            assessments.assessment_three(google_drive, file_id)
        case "all":
            assessments.assessment_one(google_drive, file_id)
            assessments.assessment_two(google_drive, file_id)
            assessments.assessment_three(google_drive, file_id)

    # close connection to Google Drive
    google_drive.connection.close()


if __name__ == "__main__":
    # set some logging formatting
    log_format = logging.Formatter("%(asctime)s - %(name)s - [%(levelname)s] -  %(message)s", "%m-%d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(log_format)
    logging.getLogger().addHandler(handler)
    logging.root.setLevel(logging.INFO)

    main()
