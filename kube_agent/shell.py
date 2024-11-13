# -*- coding: utf-8 -*-
import subprocess
from typing import List, Union
import tiktoken


class CommandExecutor():
    '''Wrapper for shell commands.'''

    def __init__(self, command, max_tokens=3000, strip_newlines: bool = False, return_err_output: bool = False):
        """Initialize with stripping newlines."""
        self.strip_newlines = strip_newlines
        self.return_err_output = return_err_output
        self.command = command
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def run(self, args: Union[str, List[str]], input=None, timeout=None) -> str:
        '''Run the command.'''
        if isinstance(args, str):
            args = [args]
        commands = ";".join(args)
        if not commands.startswith(self.command):
            commands = f'{self.command} {commands}'
        result = self.exec(commands, input=input, timeout=timeout)
        tokens = self.encoding.encode(result)
        while len(tokens) > self.max_tokens:
            result = result[:len(result) // 2]
            tokens = self.encoding.encode(result)
        return result

    def exec(self, commands: Union[str, List[str]], input=None, timeout=None) -> str:
        """Run commands and return final output."""
        if isinstance(commands, str):
            commands = [commands]
        commands = ";".join(commands)
        try:
            output = subprocess.run(
                commands,
                shell=True,
                check=True,
                input=input,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ).stdout.decode()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            if self.return_err_output:
                return error.stdout.decode()
            return str(error)
        if self.strip_newlines:
            output = output.strip()
        return output


class ScriptExecutor(CommandExecutor):
    '''Wrapper for script execution.'''

    def __init__(self, command, max_tokens=3000, strip_newlines: bool = False, return_err_output: bool = False):
        """Initialize script executor."""
        super().__init__(f'{command} -c', max_tokens, strip_newlines, return_err_output)

    def run(self, code: Union[str, List[str]], timeout=None) -> str:
        '''Run script and return output.'''
        if isinstance(code, list):
            code = '\n'.join(code)
        code = code.replace("'", "'\"'\"'")
        return super().run(f"'{code}'", timeout=timeout)
