import json
from typing import Dict, Type, Union

from pydantic import BaseModel, ValidationError

from pymetadataeditor.schemas import SchemaBaseModel


def _format_errors(errors):
    formatted_errors = []
    for error in errors:
        loc = ".".join(str(x) for x in error["loc"])
        msg = f"{error['type']}: {loc} {error['msg'].lower()}"
        formatted_errors.append(msg)
    return "\n" + "\n".join(formatted_errors)


def validate_metadata(metadata: Union[Dict, SchemaBaseModel, str], schema_definition: Type[SchemaBaseModel]) -> None:
    """
    Checks that the metadata contains the key information that all metadata must have, namely idno

    Args:
        metadata (dict or SchemaBaseModel): The metadata to be validated
        schema (str): Type of metadata being passed, must be "TimeSeries"

    Raises:
        ValueError: If the metadata is deemed invalid for whatever reason.

    """
    assert isinstance(schema_definition, type) and issubclass(schema_definition, BaseModel)
    if not isinstance(metadata, (dict, SchemaBaseModel, str)):
        raise ValueError(
            "Metadata must be passed as a python dictionary or as a pydantic object or a json string, "
            f"but {type(metadata)} was passed instead"
        )

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.decoder.JSONDecodeError as e:
            raise json.decoder.JSONDecodeError(f"This string is not valid json: '{e.doc}'", doc=e.doc, pos=e.pos)
    if isinstance(metadata, SchemaBaseModel):
        metadata = metadata.model_dump()
    try:
        # Try to parse the input dictionary using MyModel
        schema_definition(**metadata)
    except ValidationError as e:
        formatted_error_message = _format_errors(e.errors())
        raise ValueError(formatted_error_message) from None  # None stops it appearing like a new error


def update_metadata(old_object: SchemaBaseModel, **kwargs):
    """
    Updates the metadata of a given Pydantic model instance with new values provided as keyword arguments.

    Args:
        old_object (SchemaBaseModel): The original instance of a Pydantic model to be updated.
        **kwargs: Arbitrary keyword arguments representing the fields and their new values to update in the model.
                  Only the fields with non-None values will be updated.

    Returns:
        SchemaBaseModel: A new instance of the Pydantic model with updated metadata.

    Raises:
        AttributeError: If a provided field name does not exist in the model.

    Example:
        class Example(SchemaBaseModel):
            f1: int
            f2: str

        original = Example(f1=1, f2="old")
        updated = update_metadata(original, f2="new")
        print(updated)
        # Output: Example(f1=1, f2='new')
    """
    new_object = old_object.model_copy()
    for k, v in kwargs.items():
        if v is not None:
            new_object[k] = v
    return new_object
