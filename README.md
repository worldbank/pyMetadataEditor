# pyMetadataEditor

This is a work in progress python implementation of the r package metadataeditr (https://github.com/ihsn/metadataeditr).


# Setting up the python environment

This library uses Poetry for dependency management (https://python-poetry.org/docs/basic-usage/).

In your python environment run `pip install poetry` then navigate to the pymetadataeditor folder and run `poetry install` or, if that doesn't work, try `python -m poetry install`. 

## Poetry troubleshooting

If you are running on Windows and see errors about numpy installation errors then it could be an issue with Windows file paths. With default settings, file paths that exceed a few hundred characters can cause installation problems. To overcome this you can either

1) enable long path support in Windows
2) install python libraries in a folder in the current directory by running `poetry config virtualenvs.in-project true` and then running `poetry install`