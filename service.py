from functools import cached_property
from logging import Logger
from pathlib import Path
from os import PathLike
from typing import ClassVar

from google.auth.transport.requests import Request    # type: ignore
from google.oauth2.credentials import Credentials    # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow    # type: ignore
from googleapiclient.discovery import Resource, build    # type: ignore
from googleapiclient.errors import HttpError    # type: ignore
import rich
from rich.console import Console
from rich.progress import Progress, ProgressColumn, SpinnerColumn, TimeElapsedColumn



class DriveService:
    max_search_pages: ClassVar[int] = 10
    page_size: ClassVar[int] = 100
    default_columns: ClassVar[list[ProgressColumn]] = [
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        # ConditionalTransferSpeedColumn(),
    ]

    def __init__(
        self,
        *,
        log: bool = False,
        logger: Logger | None = None,
        console: Console | None = None,
        db_path: PathLike | str | bytes | None = None
    ) -> None:
        self.console = rich.get_console() if console is None else console
        self.progress = Progress(*self.default_columns)
        self.log = log
        # self.db_path: PathLike | str | bytes
        # self.logger = Logger

    def __enter__(self) -> 'DriveService':
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.service.close()
        self.progress.stop()

        if isinstance(exc_value, HttpError):
            self.progress.log(
                "[red]ERROR:[/red] While processing request.",
                exc_type, exc_value, exc_tb,
                log_locals=True
            )
            return True

    @cached_property
    def service(self) -> Resource:
        return build("drive", "v3", credentials=self.creds)

    @cached_property
    def creds(self) -> Credentials:
        """
        Check for valid credentials, and generate token.
        """
        assert isinstance(TOKEN, str) and isinstance(CREDS, str), \
            "Must Provide TOKEN and CREDS path."
        token = Path(TOKEN).expanduser()
        existing_creds = Path(CREDS).expanduser()
        creds = None
        # NOTE: token.json stores the user's access and refresh tokens.
        if token.exists():
            creds = Credentials.from_authorized_user_file(token, SCOPES)
        # if token not found, or token not valid, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    existing_creds, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token, 'w') as tk:
                tk.write(creds.to_json())
        return creds
