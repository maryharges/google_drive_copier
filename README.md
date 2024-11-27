# Systems Engineer Technical Assessment

## requirements
python version 3.12

## Instructions for obtaining client credentials

Assuming a personal GCP project exists given the steps outlined in the assessment instructions, we will need to download 
the credentials for local use into a file called `credentials.json`

Under the APIs & Services page for a given project, navigate to the `Google Drive Api`

Under `Credentials` there should exist OAuth2 credentials for the project, if not there is the option to 
create new credentials ( `+ Create Credentials`)

On the far right of the screen next to the  Delete and Edit icons for the compatible credentials, there is a Download 
symbol. Clicking on this gives you the option to `Download OAuth Client`. Clicking on this will bring up a screen with 
the Client Id, Secret, and Creation Date. Select the `Download JSON` to download the credentials.

From there, copy the downloaded credentials to a file called `credentials.json` in the root of this project. Command 
will look something like this.

```commandline
cp ~/Downloads/client_secret_***_***.apps.googleusercontent.com.json credentials.json
```

Additional info on creating services/other credentials to access Google Drive API can be found here:
https://developers.google.com/identity/protocols/oauth2

## Instructions for running assessments

This project utilizes a python package called `click` to create a cli to run individual assessments (or all)

The cli specifies `one, two, three, all` as options for which assessments to run, then optionally you can also supply
a folder id after the assessment if you wish to select a folder outside of the hardcoded value in the `config.yaml`

You are also able to supply a destination folder id to be used for assessment 3, if desired. 

If using the source file ID or destination file ID in the cli, you must also supply assessment first, if neither are supplied you 
can omit assessments and it will run all assessments by default, generating a destination ID supplied in the output of assessment 3.

if no cli options are specified all assessments will be run in order against the default `parent_file_id`

To run all assessments in order:

```commandline
python main.py
python main.py all
python main.py all source-file-id
python main.py all source-file-id destination-file-id 
```


To run a single assessment:

```commandline
python main.py one
python main.py two
python main.py three

python main.py one other-file-id
python main.py two other-file-id
python main.py three other-file-id
python main.py three other-file-id destination-file-id 
```
where the command after `main.py` will correspond to the assessment number.

## Assessment Details and Assumptions
### Assessment One
Solution for assessment one will print relevant output and also write to a `assessment_1_report.json`.

The json type was chosen for the report style for ease of use as consumable for other services and because it is a 
widely used and easily understandable format.

**Assumptions:**
* number of files and folders = total number of objects, non-nested, at the root of the source folder

### Assessment Two
**Assumptions:**

* Total nested folders _includes_ the top level folder count under the source folder id and only includes objects that 
match the folder type.

* Child objects under each top level folder _includes_ all objects, inclusive of the folder type and all other Google 
Drive file types.

**Report Data:**
Found under `assessment_2_report.json`

* `"total_nested_files"`: the total of nested file type objects under the source folder id, including top level files
* `"total_nested_folders"`: the total of nested folder type objects under the source folder id, including top level folders
* `"nested_object_counts_by_folder"`: the total of nested objects of all types under each top level folder under the source folder id
* `"total_nested_object_count"`: the total of all nested objects under the source folder id


Additionally, assessment two will write a json_object containing pertinent details about folder/file structure including
names, ids, etc. to a file called `drive_data.json` that is ingested by assessment 3.

### Assessment Three
Assessment Three will look for a file called `drive_data.json`, which is the output of assessment 2. If it is run 
without this file, it will generate the data at runtime.

This could potentially be optimized by introducing a flag into `.get_nested_objects` that generates 
the data and traverses the folder/file structure to "live copy" during the traversal. For the purposes of the 
assessment I avoided such optimization for increased code readability.

The folder id of the copy source folder is written to a report `assessment_3_report.json` and printed.

**Assumptions:**
* By default, copying a file in Google Drive will format the new file name `Copy {Name of File}`, for this project I made
the assumption that the copied files in the new destination should exactly match the original file/folder structure, so 
duplicated files are renamed with the original file name. For example `Stranger Things` will be called `Stranger Things`
instead of `Copy of Stranger Things`. To undo this choice, simply change the `copy_exact_filename` flag in the config.yaml file to `False`
* Upon first run a destination id is not provided, and instead created by the script. The ID of the new destination folder is 
provided at the end of the script run. If a destination ID is provided, the nested objects will still copy correctly but
things like the original source folder name will not be copied in lieu of the provided destination ID specification.

## Some thoughts on potential improvements

For a true production service I would make some slight adjustments. 

The first consideration I would make is adding a `copy` flag to `get_nested_objects` as a potential way of optimizing.
Currently I pull all of the data and write it to a dictionary for ingestion by `copy_nested_objects`, a copy flag could
still allow for this, but also actually run or schedule the `copy` job as the file structure is traversed.

The second thing is that default recursion depth in python is 1000, which technically can be adjusted, but even still I 
would probably consider breaking this service up in the case you end up with exceptionally large copy jobs.

For instance, I think using something like a lambda to ingest from a queue or that has some other trigger to each copy 
object could work well. Something like this pseudocode:
(I also left a comment in the actual code where I think you'd want to trigger something like this 
instead)
```
def copy(folder_data, destination_folder_id):
    for folder in folder_data:
        # copy the folder here to get where the contents should be copied to for the next lambda run
        new_folder_id = google_drive.connection.copy_folder(folder)
        if folder["nested_object_count"] != 0:
            # pass the new_folder_id as our new destination and hand off the folder's nested objects for the next lambda
            # run
            aws.trigger_lambda(folder["nested_objects"], new_folder_id)
```

So basically it would copy the contents of a folder, write the new destination folder ids and their child_objects to a
new job, and then go from there.

### services
I think a potential JIRA integration could be useful, so on particular failure cases to copy it could generate a JIRA
ticket for someone to follow up from in the future.

I also sort of view this as an offboarding tool, so upon an employee departure you would probably want to run something 
like this, which I also could imagine as a JIRA ticket.

I would also probably want to get some idea of failure rates across these types of jobs, so adding some kind of 
observability framework like openTelemetry to publish metrics or something would be a must.