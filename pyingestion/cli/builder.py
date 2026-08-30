import os
from typing import Any, cast

import click

from pyingestion.config_models import OutputConfig, PipelineConfig, TransformConfig
from pyingestion.input_stream import InputStream
from pyingestion.output_stream import OutputStream
from pyingestion.transform_stream import TransformStream


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
    config_data: object,
) -> InputStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.input_streams import InputStreamFactory

    if not isinstance(config_data, PipelineConfig):
        try:
            config_data = PipelineConfig.model_validate(config_data)
        except Exception as e:
            raise click.UsageError(f"Input configuration error: {e}")

    input_config = config_data.input
    return InputStreamFactory.create(
        input_config.type,
        input_config.pages_per_unit,
        input_config.recursive,
    )


def build_transform_stream_from_config(
    config_data: object,
) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.transform_stream import (
        ChainedTransformStream,
        TransformStreamFactory,
    )

    if not isinstance(config_data, PipelineConfig):
        try:
            config_data = PipelineConfig.model_validate(config_data)
        except Exception as e:
            raise click.UsageError(f"Transform configuration error: {e}")

    transform_data = config_data.transform
    if not transform_data:
        regex_path = config_data.regex
        if not regex_path:
            raise click.UsageError(
                "Transform section or 'regex' path is required in config."
            )
        try:
            return TransformStreamFactory.create("regex", {"config_file": regex_path})
        except ValueError as e:
            raise click.UsageError(str(e))

    def instantiate_transform(
        item: TransformConfig,
    ) -> TransformStream[Any, Any]:  # pyright: ignore[reportExplicitAny]
        t_type = item.type
        cfg = item.model_dump(exclude_none=True)
        try:
            return TransformStreamFactory.create(t_type, cfg)
        except ValueError as e:
            raise click.UsageError(str(e))

    if isinstance(transform_data, list):
        transforms = [instantiate_transform(item) for item in transform_data]
        if len(transforms) == 1:
            return transforms[0]
        return ChainedTransformStream(transforms)
    else:
        return instantiate_transform(transform_data)


def build_output_stream_from_config(
    config_data: object,
) -> OutputStream[Any]:  # pyright: ignore[reportExplicitAny]
    from pyingestion.output_stream import MultiOutputStream, OutputStreamFactory

    if not isinstance(config_data, PipelineConfig):
        try:
            config_data = PipelineConfig.model_validate(config_data)
        except Exception as e:
            raise click.UsageError(f"Output configuration error: {e}")

    output_data = config_data.output
    if not output_data:
        to_dest = config_data.to or "csv"
        out_path = "output.csv"
        if to_dest == "sqlite":
            out_path = "records.db"
        elif to_dest == "sqlite-vector":
            from pyingestion.rag_streams import SqliteVectorOutputStream
            return SqliteVectorOutputStream(db_path="vector_store.db")
        try:
            return OutputStreamFactory.create(to_dest, {"path": out_path})
        except ValueError as e:
            raise click.UsageError(str(e))

    if isinstance(output_data, str):
        to_dest = config_data.to or "csv"
        out_path = output_data
        if to_dest == "sqlite" and out_path.endswith(".csv"):
            out_path = out_path[:-4] + ".db"
        if to_dest == "sqlite-vector":
            from pyingestion.rag_streams import SqliteVectorOutputStream
            return SqliteVectorOutputStream(db_path=out_path)
        try:
            return OutputStreamFactory.create(to_dest, {"path": out_path})
        except ValueError as e:
            raise click.UsageError(str(e))

    def instantiate_output(
        item: OutputConfig,
    ) -> OutputStream[Any]:  # pyright: ignore[reportExplicitAny]
        out_type = item.type
        cfg = item.model_dump(exclude_none=True)
        if out_type == "sqlite-vector":
            from pyingestion.rag_streams import SqliteVectorOutputStream
            db_path = str(cfg.get("db_path") or cfg.get("path") or "vector_store.db")
            table_name = str(cfg.get("table_name") or cfg.get("table") or "embeddings")
            return SqliteVectorOutputStream(db_path=db_path, table_name=table_name)
        try:
            return OutputStreamFactory.create(out_type, cfg)
        except ValueError as e:
            raise click.UsageError(str(e))

    if isinstance(output_data, list):
        outputs = [instantiate_output(item) for item in output_data]
        if len(outputs) == 1:
            return outputs[0]
        return MultiOutputStream(outputs)
    else:
        return instantiate_output(output_data)
