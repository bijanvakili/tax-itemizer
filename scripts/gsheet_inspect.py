import argparse
from pprint import pprint

from oauth2client.service_account import ServiceAccountCredentials
import pygsheets
from pygsheets.client import SCOPES as PYGSHEETS_SCOPES
from pygsheets.custom_types import ValueRenderOption


def main():
    parser = argparse.ArgumentParser(description='Google Sheet Inspector')
    parser.add_argument('credentials_file', type=str)
    parser.add_argument('spreadsheet_id', type=str)
    parser.add_argument('worksheet_title', type=str)
    parser.add_argument('cell', type=str)

    args = parser.parse_args()

    gdrive_credentials = ServiceAccountCredentials.from_json_keyfile_name(
        args.credentials_file,
        PYGSHEETS_SCOPES
    )

    gsheet_client = pygsheets.authorize(credentials=gdrive_credentials)
    result = gsheet_client.get_range(
        args.spreadsheet_id,
        args.cell + ':' + args.cell,
        value_render=ValueRenderOption.FORMULA
    )

    pprint(result)


if __name__ == '__main__':
    main()
