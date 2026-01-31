"""PlantUML CLI wrapper for rendering diagrams.

Invokes PlantUML via subprocess (Java JAR or native binary) to render
PlantUML source to SVG/PNG output.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

OutputFormat = Literal["svg", "png"]


class PlantUMLError(Exception):
    """Error during PlantUML rendering."""

    pass


class PlantUMLRunner:
    """Runs PlantUML CLI to render diagrams.

    Supports multiple PlantUML backends:
    1. Java JAR (plantuml.jar)
    2. Native binary (plantuml)
    3. Docker container (plantuml/plantuml)

    The runner auto-detects available backends in priority order.
    """

    def __init__(
        self,
        plantuml_jar: str | None = None,
        java_path: str = "java",
        timeout: int = 30,
    ):
        """Initialize PlantUML runner.

        Args:
            plantuml_jar: Path to plantuml.jar (optional, auto-detects)
            java_path: Path to Java executable
            timeout: Render timeout in seconds
        """
        self.plantuml_jar = plantuml_jar
        self.java_path = java_path
        self.timeout = timeout
        self._backend: str | None = None

    def _detect_backend(self) -> str:
        """Detect available PlantUML backend.

        Returns:
            Backend type: 'jar', 'binary', 'docker', or raises error
        """
        if self._backend:
            return self._backend

        # Check for JAR file
        if self.plantuml_jar and Path(self.plantuml_jar).exists():
            self._backend = "jar"
            logger.info("plantuml_backend_detected", backend="jar", path=self.plantuml_jar)
            return "jar"

        # Check PLANTUML_JAR environment variable
        env_jar = os.environ.get("PLANTUML_JAR")
        if env_jar and Path(env_jar).exists():
            self.plantuml_jar = env_jar
            self._backend = "jar"
            logger.info("plantuml_backend_detected", backend="jar", path=env_jar)
            return "jar"

        # Check for native binary
        if shutil.which("plantuml"):
            self._backend = "binary"
            logger.info("plantuml_backend_detected", backend="binary")
            return "binary"

        # Check for Docker
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "images", "-q", "plantuml/plantuml"],
                    capture_output=True,
                    timeout=5,
                )
                if result.stdout.strip():
                    self._backend = "docker"
                    logger.info("plantuml_backend_detected", backend="docker")
                    return "docker"
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        raise PlantUMLError(
            "No PlantUML backend found. Install one of:\n"
            "  1. Set PLANTUML_JAR environment variable\n"
            "  2. Install 'plantuml' binary (apt install plantuml)\n"
            "  3. Pull Docker image: docker pull plantuml/plantuml"
        )

    def render(
        self,
        source: str,
        format: OutputFormat = "svg",
        output_path: str | None = None,
    ) -> tuple[bytes, str | None]:
        """Render PlantUML source to image.

        Args:
            source: PlantUML source code
            format: Output format ('svg' or 'png')
            output_path: Optional path to save output file

        Returns:
            Tuple of (image_bytes, output_path or None)

        Raises:
            PlantUMLError: If rendering fails
        """
        backend = self._detect_backend()

        if backend == "jar":
            image_bytes = self._render_jar(source, format)
        elif backend == "binary":
            image_bytes = self._render_binary(source, format)
        elif backend == "docker":
            image_bytes = self._render_docker(source, format)
        else:
            raise PlantUMLError(f"Unknown backend: {backend}")

        # Save to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(image_bytes)
            logger.info("plantuml_output_saved", path=output_path, size=len(image_bytes))

        return image_bytes, output_path

    def _render_jar(self, source: str, format: OutputFormat) -> bytes:
        """Render using Java JAR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "diagram.puml"
            input_file.write_text(source, encoding="utf-8")

            output_ext = "svg" if format == "svg" else "png"
            output_file = Path(tmpdir) / f"diagram.{output_ext}"

            cmd = [
                self.java_path,
                "-jar",
                self.plantuml_jar,
                f"-t{format}",
                "-charset",
                "UTF-8",
                str(input_file),
            ]

            logger.debug("plantuml_cmd", cmd=cmd)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.timeout,
                    check=True,
                )
            except subprocess.TimeoutExpired:
                raise PlantUMLError(f"PlantUML render timed out after {self.timeout}s")
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode("utf-8", errors="replace")
                raise PlantUMLError(f"PlantUML render failed: {stderr}")

            if not output_file.exists():
                stderr = result.stderr.decode("utf-8", errors="replace")
                raise PlantUMLError(f"PlantUML did not produce output: {stderr}")

            return output_file.read_bytes()

    def _render_binary(self, source: str, format: OutputFormat) -> bytes:
        """Render using native plantuml binary."""
        cmd = [
            "plantuml",
            "-p",  # Pipe mode (stdin -> stdout)
            f"-t{format}",
            "-charset",
            "UTF-8",
        ]

        logger.debug("plantuml_cmd", cmd=cmd)

        try:
            result = subprocess.run(
                cmd,
                input=source.encode("utf-8"),
                capture_output=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise PlantUMLError(f"PlantUML render timed out after {self.timeout}s")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise PlantUMLError(f"PlantUML render failed: {stderr}")

        return result.stdout

    def _render_docker(self, source: str, format: OutputFormat) -> bytes:
        """Render using Docker container."""
        cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "plantuml/plantuml",
            "-p",
            f"-t{format}",
            "-charset",
            "UTF-8",
        ]

        logger.debug("plantuml_cmd", cmd=cmd)

        try:
            result = subprocess.run(
                cmd,
                input=source.encode("utf-8"),
                capture_output=True,
                timeout=self.timeout + 10,  # Extra time for Docker overhead
            )
        except subprocess.TimeoutExpired:
            raise PlantUMLError(f"PlantUML Docker render timed out")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise PlantUMLError(f"PlantUML Docker render failed: {stderr}")

        return result.stdout

    def render_base64(
        self,
        source: str,
        format: OutputFormat = "svg",
    ) -> str:
        """Render PlantUML source and return base64-encoded result.

        Args:
            source: PlantUML source code
            format: Output format ('svg' or 'png')

        Returns:
            Base64-encoded image data
        """
        image_bytes, _ = self.render(source, format)
        return base64.b64encode(image_bytes).decode("ascii")

    def check_available(self) -> dict[str, bool | str]:
        """Check PlantUML availability.

        Returns:
            Dict with 'available' bool and 'backend' or 'error' string
        """
        try:
            backend = self._detect_backend()
            return {"available": True, "backend": backend}
        except PlantUMLError as e:
            return {"available": False, "error": str(e)}
