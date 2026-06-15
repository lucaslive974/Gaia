import os
from typing import TypeVar
from pyingestion.input_stream import InputStream
from pyingestion.transform_stream import TransformStream
from pyingestion.output_stream import OutputStream
from pyingestion.extraction_session import ExtractionSession

T_source = TypeVar("T_source")
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")


class PyIngestion:
    """
    Stateless pipeline execution runner.
    """

    def process(
        self,
        source: T_source,
        input_stream: InputStream[T_source, T_in],
        transform_stream: TransformStream[T_in, T_out],
        output_stream: OutputStream[T_out],
        session: ExtractionSession | None = None,
    ) -> bool:
        if isinstance(source, str) and not os.path.exists(source):
            msg = f"The input directory '{source}' does not exist."
            if session:
                session.error(msg)
            else:
                raise FileNotFoundError(msg)
            return False

        try:
            # Let the input_stream.read do all the work
            for unit_text in input_stream.read(source, session=session):
                if session and session.is_cancelled:
                    break

                if not unit_text.strip():
                    continue

                if session:
                    session.start_page(
                        input_stream.current_unit_index, input_stream.total_units
                    )

                try:
                    transformed = transform_stream.transform(unit_text)
                    if session:
                        session.process_page_result(
                            True,
                            input_stream.current_unit_index,
                            input_stream.total_units,
                        )
                    output_stream.write(transformed)
                except ValueError as e:
                    # Get partial results for error logging if supported by transform_stream
                    parse_test_fn = getattr(transform_stream, "parse_test", None)
                    partial_results = None
                    if parse_test_fn:
                        try:
                            partial_results, _ = parse_test_fn(unit_text)
                        except Exception:
                            pass
                    if session:
                        session.log_failed_page(
                            unit_text,
                            input_stream.current_unit_index,
                            str(e),
                            partial_results,
                        )
                        session.process_page_result(
                            False,
                            input_stream.current_unit_index,
                            input_stream.total_units,
                        )

            if session and not session.is_cancelled:
                session.complete()
            return True

        except Exception as e:
            if session:
                session.error(str(e))
            return False
