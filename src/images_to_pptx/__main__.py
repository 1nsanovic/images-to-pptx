from images_to_pptx.app import run
from images_to_pptx.ipc import request_capture
from images_to_pptx.notify import notify as os_notify


def main() -> None:
    import sys

    if "--capture" in sys.argv:
        if not request_capture():
            os_notify("Images to PPTX", "Сначала запустите приложение")
            sys.exit(1)
        return
    run()


if __name__ == "__main__":
    main()
