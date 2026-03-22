"""Tests for buffered health event logger."""

from pathlib import Path

from portmux.health.logger import HealthLogger


class TestHealthLoggerBuffer:
    def test_events_buffer_in_memory(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("test event")

        # Not on disk yet — still in buffer
        assert not log_file.exists()
        assert len(logger._buffer) == 1

    def test_explicit_flush_writes_to_disk(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("SSH alive, port open", tunnel="L:8080:localhost:80")
        logger.flush()

        content = log_file.read_text()
        assert " INFO [L:8080:localhost:80] SSH alive, port open" in content
        assert logger._buffer == []

    def test_auto_flush_on_buffer_full(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file, buffer_size=3)

        logger.info("one")
        logger.info("two")
        assert not log_file.exists()

        logger.info("three")  # triggers auto-flush

        assert log_file.exists()
        lines = log_file.read_text().splitlines()
        assert len(lines) == 3
        assert logger._buffer == []

    def test_flush_empty_noop(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.flush()  # should not create file

        assert not log_file.exists()

    def test_multiple_flushes_append(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("first")
        logger.flush()
        logger.info("second")
        logger.flush()

        lines = log_file.read_text().splitlines()
        assert len(lines) == 2


class TestHealthLoggerFormat:
    def test_info_with_tunnel(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("SSH alive", tunnel="L:8080:localhost:80")
        logger.flush()

        content = log_file.read_text()
        assert " INFO [L:8080:localhost:80] SSH alive" in content

    def test_error_with_tunnel(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.error("SSH exited (255)", tunnel="L:5432:db:5432")
        logger.flush()

        content = log_file.read_text()
        assert " ERROR [L:5432:db:5432] SSH exited (255)" in content

    def test_warning(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.warning("Port not responding", tunnel="L:8080:localhost:80")
        logger.flush()

        assert " WARNING " in log_file.read_text()

    def test_heartbeat(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.heartbeat("✓ 3/3 healthy — 14:23:15")
        logger.flush()

        assert " HEARTBEAT ✓ 3/3 healthy" in log_file.read_text()

    def test_no_tunnel(self, tmp_path):
        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("Monitor started")
        logger.flush()

        content = log_file.read_text()
        assert " INFO Monitor started" in content
        assert "[" not in content.split("INFO ")[1]

    def test_timestamp_format(self, tmp_path):
        import re

        log_file = tmp_path / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("test")
        logger.flush()

        content = log_file.read_text()
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO", content)

    def test_creates_parent_dirs(self, tmp_path):
        log_file = tmp_path / "subdir" / "health.log"
        logger = HealthLogger(log_path=log_file)

        logger.info("test")
        logger.flush()

        assert log_file.exists()


class TestHealthLoggerRead:
    def _write_lines(self, log_file, lines):
        log_file.write_text("\n".join(lines) + "\n")

    def test_read_tail(self, tmp_path):
        log_file = tmp_path / "health.log"
        lines = [f"2026-03-21 14:00:0{i} INFO line {i}" for i in range(10)]
        self._write_lines(log_file, lines)
        logger = HealthLogger(log_path=log_file)

        result = logger.read_tail(3)

        assert len(result) == 3
        assert "line 7" in result[0]
        assert "line 9" in result[2]

    def test_read_head(self, tmp_path):
        log_file = tmp_path / "health.log"
        lines = [f"2026-03-21 14:00:0{i} INFO line {i}" for i in range(10)]
        self._write_lines(log_file, lines)
        logger = HealthLogger(log_path=log_file)

        result = logger.read_head(3)

        assert len(result) == 3
        assert "line 0" in result[0]
        assert "line 2" in result[2]

    def test_read_tail_empty_file(self, tmp_path):
        logger = HealthLogger(log_path=tmp_path / "nonexistent.log")
        assert logger.read_tail(5) == []

    def test_read_head_empty_file(self, tmp_path):
        logger = HealthLogger(log_path=tmp_path / "nonexistent.log")
        assert logger.read_head(5) == []

    def test_read_tail_fewer_lines(self, tmp_path):
        log_file = tmp_path / "health.log"
        self._write_lines(log_file, ["line 1", "line 2"])
        logger = HealthLogger(log_path=log_file)

        result = logger.read_tail(10)
        assert len(result) == 2


class TestHealthLoggerRecentErrors:
    def test_recent_errors(self, tmp_path):
        from datetime import datetime, timedelta

        log_file = tmp_path / "health.log"
        now = datetime.now()
        recent = (now - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"{old} ERROR [L:8080:localhost:80] Dead: old event",
            f"{recent} INFO [L:8080:localhost:80] Healthy: alive",
            f"{recent} ERROR [L:5432:db:5432] Dead: SSH exited",
        ]
        log_file.write_text("\n".join(lines) + "\n")
        logger = HealthLogger(log_path=log_file)

        result = logger.read_recent_errors(minutes=10)

        assert len(result) == 1
        assert "L:5432:db:5432" in result[0]

    def test_recent_errors_no_file(self, tmp_path):
        logger = HealthLogger(log_path=tmp_path / "nonexistent.log")
        assert logger.read_recent_errors() == []

    def test_recent_errors_catches_vanished(self, tmp_path):
        from datetime import datetime

        log_file = tmp_path / "health.log"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"{now} ERROR [L:8080:localhost:80] Vanished: tunnel window disappeared",
        ]
        log_file.write_text("\n".join(lines) + "\n")
        logger = HealthLogger(log_path=log_file)

        result = logger.read_recent_errors(minutes=10)
        assert len(result) == 1


class TestDefaultLogPath:
    def test_default_path(self):
        logger = HealthLogger()
        assert logger.log_path == Path.home() / ".portmux" / "health.log"
