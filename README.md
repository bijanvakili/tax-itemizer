# Tax Itemizer

### Introduction

Python code used to itemize transaction records into tax categories.

Includes commands to scrape or import FX rates.

### Requirements

* python 3.9.x
* Packages in `requirements.txt`

### Setup

Choose an environment slug name (e.g. `dev`) by setting it in the `RECEIPTS_DEV` environment variable:

    export RECEIPTS_ENV=dev

Copy the `example` YAML configuration template and edit as appropriate:

    cp config/config.example.yaml config/config.dev.yaml
    vi config.dev.yaml

If you wish to use a different configuration folder, you can set it via the `RECEIPTS_CONFIG_DIR` environment variable.

Finally, run the following to initialize the database and create an initial administrative user.

    ./run.sh init_receipts

### Administration

Start up the server:

    ./run.sh web

Open the admin site in your web browser:

    open http://localhost:8000/admin/

To add more administrative users:

    ./run.sh createsuperuser

To load a payment methods YAML file:

    ./run.sh import payment_methods path/to/sample.payment_methods.yaml

To load a vendor YAML file:

    ./run.sh import vendors path/to/sample.vendors.yaml

To load a OANDA forex JSON file:

    ./run.sh import forex path/to/sample/forex.json

### Transaction processing

    ./run.sh itemize path/to/transaction_XXX.csv
    ./run.sh itemize path/to/transaction_YYY.csv
    ...
    ./run.sh export receipts <start-date> <end-date> [output_filename]

`start-date` = 'YYYY-MM-DD'
`end-date` = 'YYYY-MM-DD'

### FX Rates

To download the currency rates.

    ./run.sh download_forex <start-date> <end-date>
    ...
    ./run.sh export forex <start-date> <end-date> [output_filename]

`start-date` = 'YYYY-MM-DD'
`end-date` = 'YYYY-MM-DD'

### Google Spreadsheet Uploads

You first need to set up access.

#### Authentication

In the Google Developer's console
* Create a Service Account via the [IAM](https://console.developers.google.com/iam-admin/iam) admin page
    * Ensure at least `Editor` access
    * Download the `.json` file to `config/secrets`

#### Authorization

In the API & Services [Library](https://console.developers.google.com/apis/library) page
* Enable the `Google Drive API`
* Enable the `Google Sheets API`

In Google Drive:
* Extend your sheet's permissions to allow `Write` access to your service account.
    * This should be identified by a `iam.gserviceaccount.com` email.

#### Client Credentials

Edit the you `config/config.ENV.yaml` to set the `SPREADSHEET` entry as follows:

```yaml
SPREADSHEET:
    id: "<Google spreadsheet id goes here>",
    credentials_file: "path/to/secrets/gdrive.yaml"
```

#### Running the Upload

You can then upload data as follows:

    ./run.sh gsheet_upload <start-date> <end-date>

### Testing

Install packages in `test_requirements.txt`:

    pip install -r test_requirements.txt

For normal execution:

    ./run.sh test

NOTE: `run.sh` will force test runs to always use the `RECEIPTS_ENV=test` environment.

For repeated execution, you can reuse the same test database with models using the `--reuse-db` option.

    ./run.sh test --reuse-db
    ./run.sh test --reuse-db
    ...
    # when finished or if models changed, run the following
    rm -rf .testdb

To run code linter:

    ./run.sh lint

To set up git pre-commit hooks to run code linter, do this:

    cp scripts/pre-commit .git/hooks/pre-commit

### Requirement updates

Run the following:

    # install developer requirements
    pip install -r dev_requirements.txt

    # regenerate hash dependencies
    pip-compile --generate-hashes requirements.in --output-file requirements.txt
    pip-compile --generate-hashes test_requirements.in --output-file test_requirements.txt

### References

* [OANDA Historical Rates](https://www.oanda.com/solutions-for-business/historical-rates-beta/hcc.html) (OANDA Solutions for Business)
