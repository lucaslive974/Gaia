import os
import json
from abc import ABC, abstractmethod
from pyingestion.extraction_session import ExtractionSession


class SessionStore(ABC):
    @abstractmethod
    def load(self, source: str) -> dict | None:
        """
        Loads the session state dictionary for a given source path.
        """
        pass

    @abstractmethod
    def save(self, source: str, session: ExtractionSession) -> None:
        """
        Saves the session state dictionary for a given source path.
        """
        pass

    @abstractmethod
    def clear(self, source: str) -> None:
        """
        Clears the session state for a given source path.
        """
        pass


class FileSessionStore(SessionStore):
    def _get_paths(self, source: str) -> list[str]:
        paths = [os.path.join(os.getcwd(), ".gaia_resume.json")]
        if os.path.exists(source):
            if os.path.isdir(source):
                paths.append(os.path.join(source, ".gaia_resume.json"))
            else:
                paths.append(
                    os.path.join(
                        os.path.dirname(os.path.abspath(source)),
                        ".gaia_resume.json",
                    )
                )
        return list(set(paths))

    def load(self, source: str) -> dict | None:
        paths = self._get_paths(source)
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        state_data = json.load(f)
                        # Ensure compatibility keys
                        if (
                            "regex_file" in state_data
                            and "config_file" not in state_data
                        ):
                            state_data["config_file"] = state_data["regex_file"]
                        elif (
                            "config_file" in state_data
                            and "regex_file" not in state_data
                        ):
                            state_data["regex_file"] = state_data["config_file"]

                        if state_data.get("input_dir") == source:
                            return state_data
                except Exception:
                    pass
        return None

    def save(self, source: str, session: ExtractionSession) -> None:
        paths = self._get_paths(source)
        state_data = {
            "input_dir": source,
            "output_file": getattr(session, "output_file", None),
            "config_file": getattr(session, "config_file", None),
            "regex_file": getattr(session, "config_file", None),
            "processed_files": session.processed_files,
            "successful_pages": session.successful_pages,
            "failed_pages": session.failed_pages,
            "total_pages": session.total_pages,
        }
        for p in paths:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=4)
            except Exception:
                pass

    def clear(self, source: str) -> None:
        paths = self._get_paths(source)
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
