"""Agenda backups sem cron, privilégios administrativos ou acesso à rede do contêiner."""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from threading import Event
from zoneinfo import ZoneInfo

BACKUP_NAME = re.compile(r"^scheduled-(\d{8}T\d{12}Z)-[a-f0-9]{32}\.fhbackup$")
RETRY_DELAY = timedelta(minutes=5)
RECOVERY_DELAY = timedelta(hours=1)
MAX_ATTEMPTS = 3
JOB_TIMEOUT_SECONDS = 3600


def next_daily_run(now, zone):
    """Retorna o próximo horário das 03h no fuso local como instante UTC."""
    local = now.astimezone(zone)
    target = datetime.combine(local.date(), time(3), tzinfo=zone)
    if target <= local:
        target = datetime.combine(local.date() + timedelta(days=1), time(3), tzinfo=zone)
    return target.astimezone(timezone.utc)


class Schedule:
    """Relógio e operação injetáveis permitem verificar o agendamento sem esperar."""

    def __init__(self, run_backup, now=None, zone=None):
        self.run_backup = run_backup
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.zone = zone or ZoneInfo("America/Sao_Paulo")
        self.next_run = self.now()  # Também cobre desligamentos e instalações recentes.
        self.attempts = 0

    def tick(self):
        if self.now() < self.next_run:
            return False
        try:
            succeeded = self.run_backup() == 0
        except (OSError, subprocess.SubprocessError):
            succeeded = False
        finished = self.now()
        if succeeded:
            self.attempts = 0
            self.next_run = next_daily_run(finished, self.zone)
            print("Backup concluído; próximo agendamento às 03h no fuso configurado.", flush=True)
        else:
            self.attempts += 1
            if self.attempts < MAX_ATTEMPTS:
                self.next_run = finished + RETRY_DELAY
                print("Backup falhou; nova tentativa em 5 minutos.", file=sys.stderr, flush=True)
            else:
                self.attempts = 0
                self.next_run = finished + RECOVERY_DELAY
                print(
                    "Backup continua indisponível; nova verificação em 1 hora.",
                    file=sys.stderr,
                    flush=True,
                )
        return True

    def run(self, stopped):
        while not stopped.is_set():
            self.tick()
            seconds = max(0, (self.next_run - self.now()).total_seconds())
            # Reavalia o relógio regularmente para acompanhar ajustes de horário do host.
            stopped.wait(min(seconds, 60))


@contextmanager
def scheduler_lock(path):
    """Uma segunda réplica não inicia outro agendamento sobre os mesmos arquivos."""
    with Path(path).open("a+b") as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise RuntimeError("Outro agendador já está ativo.") from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise RuntimeError("Outro agendador já está ativo.") from None
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_job(state, external_directory, stopped):
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve().parents[1] / "run_backup.py"),
        "--state-dir",
        str(state),
    ]
    if external_directory:
        command.extend(["--external-directory", str(external_directory)])
    with subprocess.Popen(command) as process:
        elapsed = 0
        while not stopped.is_set() and elapsed < JOB_TIMEOUT_SECONDS:
            try:
                return process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                elapsed += 1
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 1


def check_health(state, now=None, max_age_hours=26):
    """Verificação leve; a rotina de backup já valida integralmente o arquivo gravado."""
    if max_age_hours < 1:
        raise ValueError("A janela de verificação precisa ser positiva.")
    state = Path(state)
    now = now or datetime.now(timezone.utc)
    status_path = state / "logs/backup-status.json"
    if status_path.is_symlink() or status_path.stat().st_size > 4096:
        raise RuntimeError("Estado de backup inválido.")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(status, dict) or status.get("success") is not True:
        raise RuntimeError("A última operação de backup falhou.")
    checked_at = datetime.fromisoformat(status["checked_at"])
    if checked_at.utcoffset() is None:
        raise ValueError("O estado do backup precisa conter um fuso.")
    maximum_age = timedelta(hours=max_age_hours)
    if not timedelta(0) <= now - checked_at <= maximum_age:
        raise RuntimeError("O estado do backup está atrasado.")
    backups = []
    for path in (state / "backups").glob("scheduled-*.fhbackup"):
        match = BACKUP_NAME.fullmatch(path.name)
        if match and path.is_file() and not path.is_symlink():
            backups.append((match.group(1), path))
    if not backups:
        raise RuntimeError("O arquivo do backup não está disponível.")
    timestamp, _path = max(backups)
    created = datetime.strptime(timestamp, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
    if not timedelta(0) <= now - created <= maximum_age:
        raise RuntimeError("O arquivo do backup está atrasado.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default="/state")
    parser.add_argument("--external-directory")
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    state = Path(args.state_dir).resolve()
    try:
        if args.healthcheck:
            check_health(state)
            return 0
        zone = ZoneInfo(args.timezone)
        stopped = Event()
        for received_signal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(received_signal, lambda *_args: stopped.set())
        with scheduler_lock(state / "logs/.backup-scheduler.lock"):
            Schedule(lambda: run_job(state, args.external_directory, stopped), zone=zone).run(
                stopped
            )
    except (OSError, RuntimeError, ValueError, KeyError, TypeError):
        print(
            "Agendador indisponível; confira configuração, permissões e estado dos backups.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
