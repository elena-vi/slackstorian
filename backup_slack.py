#!/usr/bin/env python
# -*- encoding: utf-8

import argparse
import datetime
import errno
import json
import operator
import os
import sys
import time
import slacker
import boto3
from environs import Env

__version__ = '1.0.0'

USERNAMES = 'users.json'
PUBLIC_CHANNELS = 'channels'

def mkdir_p(path):
    """Create a directory if it does not already exist.
    http://stackoverflow.com/a/600612/1558022
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def download_history(channel_info, history, path):
    """Download the message history and save it to a JSON file."""
    path = os.path.join(path, '%s.json' % channel_info['name'])

    mkdir_p(os.path.dirname(path))
    json_str = json.dumps(history, indent=2, sort_keys=True)
    with open(path, 'w') as outfile:
        outfile.write(json_str)

    save_to_s3(path, '%s.json' % channel_info['name'])

# import pdb; pdb.set_trace()

def download_public_channels(slack, outdir):
    """Download the message history for the public channels where this user
    is logged in.
    """
    channels = slack.channels()
    json_str = json.dumps(channels, indent=2)

    with open('%s/channels.json' % outdir, 'w') as outfile:
        outfile.write(json_str)

    for channel in channels:
        print('  Saving %s' % channel['name'])
        history = slack.channel_history(channel=channel)
        path = os.path.join(outdir, channel['name'])
        download_history(channel_info=channel, history=history, path=path)

def download_usernames(slack, path):
    """Download the username history from Slack."""
    json_str = json.dumps(slack.usernames, indent=2, sort_keys=True)
    with open(path, 'w') as outfile:
        outfile.write(json_str)

    save_to_s3(path, 'users.json')

class AuthenticationError(Exception):
    pass

class SlackHistory(object):
    """Wrapper around the Slack API.  This provides a few convenience
    wrappers around slacker.Slacker for the particular purpose of history
    download.
    """

    def __init__(self, token):
        self.slack = slacker.Slacker(token=token)

        # Check the token is valid
        try:
            self.slack.auth.test()
        except slacker.Error:
            raise AuthenticationError('Unable to authenticate API token.')

        self.usernames = self._fetch_user_mapping()

    def _get_history(self, channel_class, channel_id):
        """Returns the message history for a channel"""
        last_timestamp = None
        response = channel_class.history(channel=channel_id,
                                         latest=last_timestamp,
                                         oldest=0,
                                         count=1000)
        return response.body['messages']

    def _fetch_user_mapping(self):
        """Gets all user information"""
        return self.slack.users.list().body['members']

    def channels(self):
        """Returns a list of public channels."""
        return self.slack.channels.list().body['channels']

    def channel_history(self, channel):
        """Returns the message history for a channel."""
        return self._get_history(self.slack.channels, channel_id=channel['id'])

def parse_args(prog, version):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='A tool for downloading message history from Slack.  This '
                    'tool downloads the message history for all your public '
                    'channels, private channels, and direct message threads.',
        epilog='If your team is on the free Slack plan, this tool can '
               'download your last 10,000 messages.  If your team is on a paid '
               'plan, this can download your entire account history.',
        prog=prog)

    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + version)
    parser.add_argument(
        '--outdir', help='output directory', default='./backup')
    # parser.add_argument(
    #     '--token', required=True,
    #     help='Slack API token; obtain from https://api.slack.com/web')

    return parser.parse_args()

def save_to_s3(path, filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=env('aws_access_key_id'),
        aws_secret_access_key=env('aws_secret_access_key')
    )

    with open(path, "rb") as f:
        s3.upload_fileobj(f, env('bucket_name'), filename)

    print('  Uploaded %s' % filename)

def env(key):
    enviroment = Env()
    enviroment.read_env()
    return enviroment(key)

def main():
    args = parse_args(prog=os.path.basename(sys.argv[0]), version=__version__)

    try:
        slack = SlackHistory(token=env('slack_token'))
    except AuthenticationError as err:
        sys.exit(err)

    mkdir_p(args.outdir)

    usernames = os.path.join(args.outdir, USERNAMES)
    print('Saving username list to %s' % usernames)
    download_usernames(slack, path=usernames)

    public_channels = args.outdir
    print('Saving public channels to %s' % public_channels)
    download_public_channels(slack, outdir=public_channels)

    # slackarino = slacker.Slacker(env('slack_token'))
    # slackarino.chat.post_message("elena-onboarding", "🐰🐰🐰")

    print('bunnies %s' % '🐰🐰🐰')
if __name__ == '__main__':
    main()











#
