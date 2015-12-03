import os
import sys
import getpass
import argparse
import scm
from .repositories import download_file
from .repositories import create_repository
from .repositories import update_repository
from .repositories import delete_repository
from .repositories import get_user_repos
from .config import USERNAME, PASSWORD, SCM, PROTOCOL
from requests.exceptions import HTTPError


def password(func):
    # very basic password input
    def decorator(args):
        if not args.password:
            args.password = getpass.getpass('password: ')
        func(args)
    return decorator


def display_repo_info(repo_info):
    repo_info['private'] = '-' if repo_info['is_private'] else '+'
    print '[{private}{scm: >4}] {owner}/{slug}'.format(**repo_info)


@password
def create_command(args):
    result = create_repository(args.reponame,
                               args.username,
                               args.password,
                               args.scm,
                               args.private)
    print ''
    print 'Repository successfully created.'
    display_repo_info(result)


@password
def update_command(args):
    update_repository(args.username,
                      args.reponame,
                      args.password,
                      scm=args.scm,
                      private=args.private)


@password
def delete_command(args):
    result = delete_repository(args.username,
                               args.reponame,
                               args.password)
    if result:
        print '{0}/{1} was deleted.'.format(args.username, args.reponame)
    else:
        print 'repository deletion failed!'


@password
def clone_command(args):
    scm.clone(args.protocol,
              args.ownername,
              args.reponame,
              args.username,
              args.password)


def pull_command(args):
    scm.pull(args.protocol,
             args.ownername,
             args.reponame)


@password
def create_from_local(args):
    scm_type = scm.detect_scm()
    if scm_type:
        reponame = os.path.basename(os.getcwd()).lower()
        try:
            create_repository(reponame, args.username, args.password,
                              scm_type, args.private)
        except Exception, e:
            print e
        scm.add_remote(args.protocol, args.username, reponame)
        scm.push_upstream()
    else:
        print('Could not detect a git or hg repo in your current directory.')


def download_command(args):
    download_file(args.ownername, args.reponame, args.filename,
                  args.username, args.password)
    print "Successfully downloaded " + args.filename


@password
def list_command(args):
    response = get_user_repos(args.username, args.password)
    for repo in response:
        display_repo_info(repo)
    print '{0} repositories listed'.format(len(response))


def run():
    # root command parser
    p = argparse.ArgumentParser(description='Interact with BitBucket',
            usage='bitbucket <command> [<args>]',
            epilog='See `bitbucket <command> --help` for more information on a specific command.')

    def add_standard_args(parser, args_to_add):
        # each command has a slightly different use of these arguments,
        # therefore just add the ones specified in `args_to_add`.
        if 'username' in args_to_add:
            parser.add_argument('--username', '-u', default=USERNAME,
                            help='your bitbucket username')
        if 'password' in args_to_add:
            parser.add_argument('--password', '-p', default=PASSWORD,
                            help='your bitbucket password')
        if 'private' in args_to_add:
            parser.add_argument('--private', '-c', action='store_true',
                            dest='private',
                            default=True,
                            help='make this repo private')
        if 'public' in args_to_add:
            parser.add_argument('--public ', '-o', action='store_false',
                            dest='private',
                            default=True,
                            help='make this repo private')
        if 'scm' in args_to_add:
            parser.add_argument('--scm', '-s', default=SCM,
                            help='which scm to use (git|hg)')
        if 'protocol' in args_to_add:
            parser.add_argument('--protocol', '-P', default=PROTOCOL,
                            help=('which network protocol '
                                  'to use (https|ssh)'))
        if 'ownername' in args_to_add:
            parser.add_argument('ownername',
                            type=str,
                            help='bitbucket account name')
        if 'reponame' in args_to_add:
            parser.add_argument('reponame',
                            type=str,
                            help='the bitbucket repository name')

    command_names = ('create', 'update', 'delete', 'clone', 'pull', 'download', 'list')
    # SUBPARSER
    subp = p.add_subparsers(title='Commands', metavar='\n  '.join(command_names))

    # CREATE COMMAND PARSER
    create_cmd_parser = subp.add_parser('create',
                            usage=('bitbucket create [-h] [--username USERNAME]\n'
                                   '                        [--password PASSWORD] [--private | --public]\n'
                                   '                        [--scm SCM] [--protocol PROTOCOL]\n'
                                   '                        reponame'),
                            description='create a new bitbucket repository')
    add_standard_args(create_cmd_parser,
                      ('username',
                       'password',
                       'protocol',
                       'private',
                       'public',
                       'scm',
                       'reponame'))
    create_cmd_parser.set_defaults(func=create_command)

    #
    # UPDATE COMMAND PARSER
    #
    update_cmd_parser = subp.add_parser('update',
                            usage=('bitbucket update [-h] [--username USERNAME]\n'
                                   '                        [--password PASSWORD] [--private | --public]\n'
                                   '                        [--scm SCM] [--protocol PROTOCOL]\n'
                                   '                        reponame'),
                            description='update an existing bitbucket repository')
    add_standard_args(update_cmd_parser,
                      ('username',
                       'password',
                       'protocol',
                       'private',
                       'scm',
                       'ownername',
                       'reponame'))
    update_cmd_parser.set_defaults(func=update_command)

    #
    # DELETE COMMAND PARSER
    #
    delete_cmd_parser = subp.add_parser('delete',
                            usage=('bitbucket delete [-h] [--username USERNAME]\n'
                                   '                        [--password PASSWORD]\n'
                                   '                        reponame'),
                            description='delete an existing bitbucket repository')
    add_standard_args(delete_cmd_parser,
                      ('username',
                       'reponame',
                       'password'))
    delete_cmd_parser.set_defaults(func=delete_command)

    #
    # CLONE COMMAND PARSER
    #
    clone_cmd_parser = subp.add_parser('clone',
                            usage=('bitbucket clone [-h] [--username USERNAME]\n'
                                   '                        [--password PASSWORD]\n'
                                   '                        [--protocol PROTOCOL]\n'
                                   '                        ownername\n'
                                   '                        reponame'),
                            description='clone a bitbucket repository')
    add_standard_args(clone_cmd_parser,
                      ('username',
                       'password',
                       'protocol'
                       'ownername',
                       'reponame'))
    clone_cmd_parser.set_defaults(func=clone_command)

    #
    # PULL COMMAND PARSER
    #
    pull_cmd_parser = subp.add_parser('pull',
                            usage=('bitbucket pull [-h] [--protocol PROTOCOL]\n'
                                   '                        ownername\n'
                                   '                        reponame'),
                            description='pull....')
    add_standard_args(pull_cmd_parser,
                      ('protocol',
                       'ownername',
                       'reponame'))
    pull_cmd_parser.set_defaults(func=pull_command)

    #
    # CREATE-FROM-LOCAL COMMAND PARSER
    #
    create_from_local_cmd_parser = subp.add_parser('create_from_local',
                            usage=('bitbucket create_from_local [-h]\n'
                                   '                        [--username USERNAME]\n'
                                   '                        [--password PASSWORD] [--private | --public]\n'
                                   '                        [--scm SCM] [--protocol PROTOCOL]\n'
                                   '                        ownername\n'
                                   '                        reponame'),
                            description='create a bitbucket repo from existing local repo')
    add_standard_args(create_from_local_cmd_parser,
                      ('username',
                       'password',
                       'protocol',
                       'private',
                       'scm',
                       'ownername',
                       'reponame'))
    create_from_local_cmd_parser.set_defaults(func=create_from_local)

    #
    # DOWNLOAD COMMAND PARSER
    #
    download_cmd_parser = subp.add_parser('download',
                            usage=('bitbucket download [-h] [--username USERNAME]\n'
                                   '                        [--password PASSWORD]\n'
                                   '                        ownername\n'
                                   '                        reponame\n'
                                   '                        filename'),
                            description='download a file from a bitbucket repo')
    add_standard_args(download_cmd_parser,
                      ('username',
                       'password',
                       'ownername',
                       'reponame'))
    download_cmd_parser.add_argument('filename', type=str,
                                     help='the file you want to download')
    download_cmd_parser.set_defaults(func=download_command)

    #
    # LIST COMMAND PARSER
    #
    list_cmd_parser = subp.add_parser('list',
                            usage=('bitbucket list [-h] [--username USERNAME]\n'
                                   '                          [--password PASSWORD]'),
                            description='list all bitbucket repos')
    add_standard_args(list_cmd_parser,
                      ('username',
                       'password'))
    list_cmd_parser.set_defaults(func=list_command)

    try:
        args = p.parse_args()
        args.func(args)
        sys.exit(0)
    except HTTPError as ex:
        print ex
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as ex:
        print 'Unhandled error: {0}'.format(ex)
        sys.exit(1)
