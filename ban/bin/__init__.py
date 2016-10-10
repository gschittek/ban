#!/usr/bin/env python
from ban.commands.helpers import load_commands
from ban.commands import parser

from ban.http.api import app


def main():
    with app.app_context():
        load_commands()
        args = parser.parse_args()
        args.func(args)


if __name__ == "__main__":
    main()
