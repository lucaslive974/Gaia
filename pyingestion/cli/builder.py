import os
import click
from collections.abc import Mapping
from typing import Any, cast

from pyingestion.input_stream import InputStream
from pyingestion.transform_stream import TransformStream
from pyingestion.output_stream import OutputStream


def load_config_file(file_path: str) -> dict[str, object]:
    import json
    import tomllib

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".toml":
            with open(file_path, "rb") as f:
                return cast(dict[str, object], tomllib.load(f))
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return cast(dict[str, object], json.load(f))
    except Exception as e:
        raise click.ClickException(f"Error loading config file: {e}")


def build_input_stream_from_config(
    config_data: Mapping[str, object],
) -> InputStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.input_streams import InputStreamFactory

    input_section = config_data.get("input")
    if isinstance(input_section, dict):
        input_type = input_section.get("type", "pdf")
        pages_per_unit = int(input_section.get("pages_per_unit", 1))
        recursive = bool(input_section.get("recursive", False))
        return InputStreamFactory.create(input_type, pages_per_unit, recursive)
    return InputStreamFactory.create("pdf")


def build_transform_stream_from_config(
    config_data: Mapping[str, object],
) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.transform_stream import NativeRegexEngine, ChainedTransformStream

    transform_data = config_data.get("transform")
    if not transform_data:
        regex_path = config_data.get("regex")
        if not isinstance(regex_path, str):
            raise click.UsageError(
                "Transform section or 'regex' path is required in config."
            )
        return NativeRegexEngine.from_file(regex_path)

    def instantiate_transform(
        item: Mapping[str, object],
    ) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
        t_type = str(item.get("type", ""))
        if t_type == "regex":
            rules_file = item.get("config_file") or item.get("rules_file")
            if not isinstance(rules_file, str):
                raise click.UsageError(
                    "Transform of type 'regex' requires 'config_file' or 'rules_file'."
                )
            return NativeRegexEngine.from_file(rules_file)
        else:
            raise click.UsageError(f"Unknown transform type: {t_type}")

    if isinstance(transform_data, list):
        transforms = [instantiate_transform(item) for item in transform_data]
        if len(transforms) == 1:
            return transforms[0]
        return ChainedTransformStream(transforms)
    elif isinstance(transform_data, dict):
        return instantiate_transform(transform_data)

    raise click.UsageError(
        "The 'transform' section must be a dictionary or a list of dictionaries."
    )


def build_output_stream_from_config(
    config_data: Mapping[str, object],
) -> OutputStream[Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.output_stream import OutputStreamFactory, MultiOutputStream

    output_data = config_data.get("output")
    if not output_data:
        to_dest = str(config_data.get("to", "csv"))
        out_path = str(config_data.get("output", "output.csv"))
        if to_dest == "sqlite" and out_path.endswith(".csv"):
            out_path = out_path[:-4] + ".db"
        try:
            return OutputStreamFactory.create(to_dest, {"path": out_path})
        except ValueError as e:
            raise click.UsageError(str(e))

    def instantiate_output(
        item: Mapping[str, object],
    ) -> OutputStream[Any]:  # pyright: ignore[reportExplicitAny]
        out_type = str(item.get("type", ""))
        try:
            return OutputStreamFactory.create(out_type, item)
        except ValueError as e:
            raise click.UsageError(str(e))

    if isinstance(output_data, list):
        outputs = [instantiate_output(item) for item in output_data]
        if len(outputs) == 1:
            return outputs[0]
        return MultiOutputStream(outputs)
    elif isinstance(output_data, dict):
        return instantiate_output(output_data)

    raise click.UsageError(
        "The 'output' section must be a dictionary or a list of dictionaries."
    )
