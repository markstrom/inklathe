import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "inklathe.app:app",
        host=os.getenv("INKLATHE_HOST", "127.0.0.1"),
        port=int(os.getenv("INKLATHE_PORT", "8787")),
        reload=False,
    )


if __name__ == "__main__":
    main()
