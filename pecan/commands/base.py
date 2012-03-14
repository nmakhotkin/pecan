import pkg_resources
import os.path
import argparse
import logging
import sys
from warnings import warn
from pecan import load_app

log = logging.getLogger(__name__)


class CommandManager(object):
    """ Used to discover `pecan.command` entry points. """

    def __init__(self):
        self.commands_ = {}
        self.load_commands()

    def load_commands(self):
        for ep in pkg_resources.iter_entry_points('pecan.command'):
            log.debug('%s loading plugin %s', self.__class__.__name__, ep)
            try:
                cmd = ep.load()
                assert hasattr(cmd, 'run')
            except Exception, e:
                warn("Unable to load plugin %s: %s" % (ep, e), RuntimeWarning)
                continue
            self.add({ep.name: cmd})

    def add(self, cmd):
        self.commands_.update(cmd)

    @property
    def commands(self):
        return self.commands_


class CommandRunner(object):
    """ Dispatches `pecan` command execution requests. """

    def __init__(self):
        self.manager = CommandManager()
        self.parser = argparse.ArgumentParser(
            version='Pecan %s' % self.version,
            add_help=True
        )
        self.parse_commands()

    def parse_commands(self):
        subparsers = self.parser.add_subparsers(
            dest='command_name',
            metavar='command'
        )
        for name, cmd in self.commands.items():
            sub = subparsers.add_parser(
                name,
                help=cmd.summary
            )
            for arg in getattr(cmd, 'arguments', tuple()):
                arg = arg.copy()
                sub.add_argument(arg.pop('command'), **arg)

    def run(self, args):
        ns = self.parser.parse_args(args)
        self.commands[ns.command_name]().run(ns)

    @classmethod
    def handle_command_line(cls):
        runner = CommandRunner()
        exit_code = runner.run(sys.argv[1:])
        sys.exit(exit_code)

    @property
    def version(self):
        try:
            dist = pkg_resources.get_distribution('Pecan')
            if os.path.dirname(os.path.dirname(__file__)) == dist.location:
                return dist.version
            else:
                return '(development)'
        except:
            return '(development)'

    @property
    def commands(self):
        return self.manager.commands_


class BaseCommand(object):
    """ Base class for Pecan commands. """

    class __metaclass__(type):
        @property
        def summary(cls):
            return cls.__doc__.strip().splitlines()[0].rstrip('.')

    arguments = ({
        'command': 'config_file',
        'help': 'a Pecan configuration file'
    },)

    def run(self, args):
        self.args = args

    def load_app(self):
        if not os.path.isfile(self.args.config_file):
            raise RuntimeError('`%s` is not a file.' % self.args.config_file)
        return load_app(self.args.config_file)
