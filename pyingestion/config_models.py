from pydantic import BaseModel, Field, model_validator


class InputConfig(BaseModel):
    type: str = "pdf"
    pages_per_unit: int = Field(default=1, ge=1)
    recursive: bool = False


class TransformConfig(BaseModel):
    type: str = "regex"
    config_file: str | None = None
    rules_file: str | None = None

    @model_validator(mode="before")
    @classmethod
    def resolve_rules_file(cls, data: object) -> object:
        if isinstance(data, dict):
            cf = data.get("config_file") or data.get("rules_file")
            if cf:
                data["config_file"] = cf
                data["rules_file"] = cf
        return data


class OutputConfig(BaseModel):
    type: str = "csv"
    path: str | None = None
    db_path: str | None = None
    connection: str | None = None
    connection_uri: str | None = None
    table: str | None = None
    table_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: object) -> object:
        if isinstance(data, dict):
            table = data.get("table_name") or data.get("table")
            if table:
                data["table"] = table
                data["table_name"] = table
            conn = data.get("connection_uri") or data.get("connection")
            if conn:
                data["connection"] = conn
                data["connection_uri"] = conn
            path_val = data.get("db_path") or data.get("path")
            if path_val:
                data["db_path"] = path_val
                data["path"] = path_val
        return data


class PipelineConfig(BaseModel):
    input_dir: str | None = None
    source: str | None = None
    regex: str | None = None
    to: str | None = None
    input: InputConfig = Field(default_factory=InputConfig)
    transform: TransformConfig | list[TransformConfig] | None = None
    output: OutputConfig | list[OutputConfig] | str | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_root_source(cls, data: object) -> object:
        if isinstance(data, dict):
            src = data.get("input_dir") or data.get("source")
            if src:
                data["input_dir"] = src
                data["source"] = src
        return data
