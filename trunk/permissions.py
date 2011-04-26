#!/usr/bin/python2.6
#
# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility to push and publish permissions.

  permissions.py [flags] COMMAND

Note the --db=DBSPEC flag is required for copy/publish/push commands and may
be required for push/test depending on your permissions configuration.
Examples:
  --db=dbhost#:::dbname#
  --db=dbhost#:otheruser::dbname#

The --set and --file flags are required for some commands.

Hashing and encryption:
  decrypt-hash
    Prompt for an encrypted string and print its hash decrypted with
    --private_keyfile.
  encrypt-password
    Prompt for a password and print its hash encrypted with --public_keyfile.
  generate-key
    Generate encryption keys and write them to --public_keyfile and
    --private_keyfile.
  hash-password
    Prompt for a password and print its MySQL hash.

Using a permissions file and admin permissions tables:
  copy
    Copy the published permissions --set to --db.
  dump
    Dump the SQL for the permissions --set from --file.
  list-sets
    List the permissions set names defined in --file.
  publish
    Publish the permissions set --source_set from --file to --db as --set.
  push
    Push permissions set --source_set from --file directly to --db.
  test
    Test all permissions sets defined in --file.
"""

__author__ = 'flamingcow@google.com (Ian Gulliver)'

import inspect
import sys

from permissions_lib import define
from permissions_lib import use
from permissions_lib import utils
from pylib import app
from pylib import flags
from pylib import db

FLAGS = flags.FLAGS

flags.DEFINE_string('db', None, 'DB spec to read from/push to')
flags.DEFINE_integer('push_duration', None,
                     'Staggered push duration (seconds)')
flags.DEFINE_string('file', None,
                    'File containing permissions settings on which to '
                    'operate. The file may contain one or more named sets of '
                    'permissions')
flags.DEFINE_string('public_keyfile', None,
                    'File to write/read public encryption key to/from')
flags.DEFINE_string('private_keyfile', None,
                    'File to write/read private encryption key to/from')
flags.DEFINE_integer('key_bits', None,
                     'Size (in bits) of new RSA key')
flags.DEFINE_string('set', None,
                    'Set name to publish to')
flags.DEFINE_string('source_set', None,
                    'Set name to publish from; defaults to target set')


_COMMANDS = {'decrypt-hash':     utils.DecryptHashInteractive,
             'encrypt-password': utils.EncryptPasswordInteractive,
             'generate-key':     utils.GenerateKey,
             'hash-password':    utils.HashPasswordInteractive,
             'copy':             use.Copy,
             'dump':             use.PermissionsFile.Dump,
             'list-sets':        use.PermissionsFile.PrintSets,
             'push':             use.PermissionsFile.Push,
             'publish':          use.PermissionsFile.Publish,
             'test':             use.PermissionsFile.Test}


def CheckArgs(func, args):
  argset = set(args)
  spec = inspect.getargspec(func)
  if spec.defaults:
    funcargs = set(spec.args[:-len(spec.defaults)])
  else:
    funcargs = set(spec.args)
  missing = funcargs.difference(argset)
  if missing:
    raise app.UsageError('Missing arguments: %s' % ', '.join(missing))
  for extra in argset.difference(funcargs):
    del args[extra]


def main(argv):
  if len(argv) != 2:
    raise app.UsageError('Incorrect arguments')

  args = {}

  if FLAGS.private_keyfile:
    args['private_keyfile'] = FLAGS.private_keyfile

  if FLAGS.file:
    args['self'] = use.PermissionsFile(open(FLAGS.file, 'r').read(),
                                       private_keyfile=FLAGS.private_keyfile)
    args.pop('private_keyfile', None)  # Not otherwise used

  if FLAGS.db:
    args['dbh'] = db.Connect(FLAGS.db)

  if FLAGS.set:
    args['dest_set_name'] = FLAGS.set
    args['set_name'] = FLAGS.set

  if FLAGS.source_set:
    args['set_name'] = FLAGS.source_set

  if FLAGS.push_duration:
    args['push_duration'] = FLAGS.push_duration

  if FLAGS.public_keyfile:
    args['public_keyfile'] = FLAGS.public_keyfile

  CheckArgs(_COMMANDS[argv[1]], args)
  try:
    try:
      obj = args.pop('self')
      _COMMANDS[argv[1]](obj, **args)
    except KeyError:
      _COMMANDS[argv[1]](**args)
  except db.Error, e:
    # Lose the stack trace; it's not useful for DB errors
    print e
    return 1
  finally:
    if 'dbh' in args:
      args['dbh'].Close()


if __name__ == '__main__':
  app.run()
