from typing import Generator, Any, Generic, TypeVar

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")


class InputStream(Generic[T_out]):
    output_type: type[T_out] = Any

    def read(self, source: Any) -> Generator[T_out, None, None]:
        raise NotImplementedError


class TransformStream(Generic[T_in, T_out]):
    input_type: type[T_in] = Any
    output_type: type[T_out] = Any

    def transform(self, data: T_in) -> T_out:
        raise NotImplementedError


class OutputStream(Generic[T_in]):
    input_type: type[T_in] = Any

    def write(self, item: T_in) -> None:
        raise NotImplementedError


class MultiOutputStream(OutputStream[T_in]):
    input_type: type[T_in] = Any

    def __init__(self, streams: list[OutputStream[T_in]]):
        self.streams = streams
        if streams:
            self.input_type = streams[0].input_type

    def write(self, item: T_in) -> None:
        for stream in self.streams:
            stream.write(item)


class ParallelTransformStream(TransformStream[T_in, dict]):
    input_type: type[T_in] = Any
    output_type: type[dict] = dict

    def __init__(self, transforms: list[TransformStream[T_in, dict]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type

    def transform(self, data: T_in) -> dict:
        result = {}
        for transform in self.transforms:
            res = transform.transform(data)
            if isinstance(res, dict):
                result.update(res)
        return result


class ChainedTransformStream(TransformStream[Any, Any]):
    def __init__(self, transforms: list[TransformStream[Any, Any]]):
        self.transforms = transforms
        if transforms:
            self.input_type = transforms[0].input_type
            self.output_type = transforms[-1].output_type

    def transform(self, data: Any) -> Any:
        current = data
        for transform in self.transforms:
            current = transform.transform(current)
        return current
