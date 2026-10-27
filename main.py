"""MixaPozioni - punto di ingresso."""
import os
import sys
import traceback


def _enable_dpi_awareness() -> None:
    """Su Windows evita che il sistema ingrandisca (e sfoca) la finestra."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    _enable_dpi_awareness()
    from game.game import Game

    try:
        Game().run()
    except Exception:
        # In modalità --windowed non c'è console: salviamo l'errore su file.
        log = os.path.join(os.path.expanduser("~"), "MixaPozioni_errore.txt")
        try:
            with open(log, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
