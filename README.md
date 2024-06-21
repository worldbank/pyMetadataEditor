# pyMetadataEditor

Go to demo.ipynb to see examples of how to use this tool.

This is a work in progress python implementation of the r package metadataeditr (https://github.com/ihsn/metadataeditr).


## Setting up the python environment

This library uses Poetry for dependency management (https://python-poetry.org/docs/basic-usage/).

In your python environment run `pip install poetry` then navigate to the pymetadataeditor folder and run `poetry install` or, if that doesn't work, try `python -m poetry install`.

### Development python environment

If you want to make changes to this repo then you also need to install the tools used for development but which aren't used otherwise, for example pytest.

Run:

`poetry install --with dev`
`poetry run pre-commit install`

### Poetry troubleshooting

If you are running on Windows and see errors about numpy installation errors then it could be an issue with Windows file paths. With default settings, file paths that exceed a few hundred characters can cause installation problems. To overcome this you can either

1) enable long path support in Windows (https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#enable-long-paths-in-windows-10-version-1607-and-later)
2) install python libraries in a folder in the current directory by running `poetry config virtualenvs.in-project true` and then running `poetry install`

## New Schemas

To create new pydantic schemas based on json schema definitions, download new json schema definitions and put them in the folder `pymetadataeditor\schemas\jsonschema` and then, in the dev poetry environment, run the following command changing the input and output filenames as appropriate:

`datamodel-codegen --input pymetadataeditor/schemas/jsonschema/timeseries-schema.json --input-file-type jsonschema --reuse-model --use-schema-description --target-python-version 3.11 --use-double-quotes --wrap-string-literal --base-class ...tools.SchemaBaseModel --output-model-type pydantic_v2.BaseModel --output pymetadataeditor/schemas/pydantic_definitions/timeseries_schema.py`

### New Schema Troubleshooting

The error information from datamodel-codegen is not usually, and using the `--debug` often not helpful either.

If the json schema definition contains `"$ref": ` then make sure to download the associated file and also place it in `pymetadataeditor\schemas\jsonschema`.

## Notes

In keeping with World Bank Group practice, it should be noted that parts of this code base were written with the assistance of ChatGPT.