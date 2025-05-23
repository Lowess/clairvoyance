import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict

from clairvoyance.notifiers.notifier import Notifier


class TrivyTableNotifier(Notifier):
    __logger = logging.getLogger(__name__)

    def __repr__(self) -> str:
        return f"{str(self.__class__.__name__)} configured to notify with Trivy table format"

    def _trigger_trivy_convert(self, trivy_output_json):
        try:
            trivy_cmd = [
                "trivy",
                "convert",
                "--format",
                "table",
                trivy_output_json,
            ]
            self.__logger.info(f"Invoking Trivy scan command: {' '.join(trivy_cmd)}")
            result = subprocess.run(
                trivy_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Error running Trivy: {e.stderr}")
            return {}

    def send(self, subject: str, message: Dict[str, Any]) -> None:
        for report_types in ["Image", "Fs"]:
            with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp_file:
                # Dump the JSON data into the temporary file
                json.dump(message["RawReports"][report_types], temp_file)

                # Important: flush the buffer so the data is physically written to disk
                temp_file.flush()

                # You can access the temporary file's name
                self._trigger_trivy_convert(temp_file.name)
