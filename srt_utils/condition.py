import logging
import subprocess
import sys
import time
import typing

from srt_utils.enums import Status
from srt_utils.exceptions import SrtUtilsException


logger = logging.getLogger(__name__)


SSH_CONNECTION_TIMEOUT = 10


class Condition:

    def __init__(self, args: typing.List[str], via_ssh: bool=False):
        """
        Helper class to work with Python `subprocess` module.

        Attributes:
            args:
                The arguments used to launch the process.
            via_ssh:
                True/False depending on whether the arguments `args` contain
                SSH related ones.
        """
        self.args = args
        # TODO: change via_ssh to timeouts (for start, for stop - depending on object and
        # whether it is started via ssh or locally)
        self.via_ssh = via_ssh
        self.process = None
        self.id = None
        self.is_started = False
        self.is_stopped = False

    def __str__(self):
        return f'process id {self.id}'

    @property
    def status(self):
        """
        Get process status.

        Returns:
            A tuple of status and returncode depending on process status.

        Possible combinations:
            (Status.idle, None):
                If the process has not been started yet,
            (Status.running, None):
                If the process has been started successfully and still running
                at the moment of getting status,
            (Status.idle, some returncode):
                If the process has been started successfully, but is not
                running at the moment of getting status.
        """
        if self.process.stderr:
            return Status.idle, None

        else:
            return Status.running, ''

    def start(self):
        """
        Start process.

        Raises:
            SrtUtilsException
        """
        logger.debug(f'Starting process')

        if self.is_started:
            raise SrtUtilsException(
                f'Process has been started already: {self.id}. '
                'Start can not be done'
            )

        try:
            if sys.platform == 'win32':
                self.process = subprocess.run(
                    self.args,
                    stdin =subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=False,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    bufsize=1
                )
            else:
                self.process = subprocess.run(
                    self.args,
                    stdin =subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1
                )
                self.is_started = True
        except OSError as error:
            raise SrtUtilsException(
                f'Process has not been started: {self.args}. {error}'
            )

        # TODO: Adjust timers
        # Check that the process has started successfully and has not terminated
        # because of an error
        if self.via_ssh:
            time.sleep(SSH_CONNECTION_TIMEOUT + 1)
        else:
            # FIXME: Find a better solution, I changed the time from 1 to 5 s,
            # cause it was not enough in case of errors with srt-test-messaging
            # app, e.g. when starting the caller first and there is no listener yet
            # NOTE: A good thing to consider - what would be in case the child process
            # finfishes its work earlier than the time specified (5s). It is
            # important to consider especially in case of fsrt and small files
            # transmission.
            time.sleep(5)

        status, returncode = self.status
        if self.process.stderr.decode("utf-8"):
            raise SrtUtilsException(
                f'Process has not been started: {self.args}, returncode: '
                f'{returncode}, stdout: {self.process.stdout.decode("utf-8")}, '
                f'stderr: {self.process.stderr.decode("utf-8")}'
            )

        self.id = ''

    def stop(self):
        self.is_stopped = True
