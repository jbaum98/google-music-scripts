import os
import sys

import click
import google_music
import google_music_utils as gm_utils
from click_default_group import DefaultGroup
from logzero import logger

from google_music_scripts.__about__ import __title__, __version__
from google_music_scripts.cli import CustomPath, default_to_cwd, split_filter_strings
from google_music_scripts.config import configure_logging
from google_music_scripts.core import (
	download_songs, filter_songs, get_local_songs, upload_songs
)
from google_music_scripts.utils import template_to_base_path


@click.group(cls=DefaultGroup, default='up', default_if_no_args=True)
@click.version_option(__version__, '-V', '--version', prog_name=__title__, message="%(prog)s %(version)s")
def sync():
	"""Sync songs to/from a Google Music library."""

	pass


@sync.command('down')
@click.version_option(__version__, '-V', '--version', prog_name=__title__, message="%(prog)s %(version)s")
@click.option('-l', '--log', is_flag=True, default=False, help="Log to file.")
@click.option('-v', '--verbose', count=True)
@click.option('-q', '--quiet', count=True)
@click.option('-n', '--dry-run', is_flag=True, default=False, help="Output list of songs that would be downloaded.")
@click.option(
	'-u', '--username', metavar='USERNAME', default='',
	help="Your Google username or e-mail address.\nUsed to separate saved credentials."
)
@click.option(
	'--uploader-id', metavar='ID',
	help="A unique id given as a MAC address (e.g. '00:11:22:33:AA:BB').\nThis should only be provided when the default does not work."
)
@click.option(
	'--no-recursion', is_flag=True, default=False,
	help="Disable recursion when scanning for local files.\nRecursion is enabled by default."
)
@click.option(
	'--max-depth', metavar='DEPTH', type=int,
	help="Set maximum depth of recursion when scanning for local files.\nDefault is infinite recursion."
)
@click.option(
	'-f', '--include-filter', metavar='FILTER', multiple=True, callback=split_filter_strings,
	help="Metadata filters to match Google songs.\nSongs can match any filter criteria."
)
@click.option(
	'-fa', '--all-includes', is_flag=True, default=False,
	help="Songs must match all include filter criteria to be included."
)
@click.option(
	'-F', '--exclude-filter', metavar='FILTER', multiple=True, callback=split_filter_strings,
	help="Metadata filters to match Google songs.\nSongs can match any filter criteria."
)
@click.option(
	'-Fa', '--all-excludes', is_flag=True, default=False,
	help="Songs must match all exclude filter criteria to be included."
)
@click.option(
	'-o', '--output', metavar='TEMPLATE_PATH', default=os.getcwd(), type=CustomPath(),
	help="Output file or directory name which can include template patterns."
)
@click.argument('include-paths', nargs=-1, type=CustomPath(resolve_path=True))
def sync_down(
	log, verbose, quiet, dry_run, username, uploader_id, no_recursion, max_depth,
	include_filter, all_includes, exclude_filter, all_excludes, output, include_paths):
	"""Sync songs from a Google Music library."""

	configure_logging(verbose - quiet, log_to_file=log)

	logger.info("Logging in to Google Music")
	mm = google_music.musicmanager(username, uploader_id=uploader_id)

	if not mm.is_authenticated:
		sys.exit("Failed to authenticate client.")

	if no_recursion:
		max_depth = 0
	elif max_depth is None:
		max_depth = float('inf')

	google_songs = filter_songs(
		mm.songs(),
		include_filters=include_filter, all_includes=all_includes,
		exclude_filters=exclude_filter, all_excludes=all_excludes
	)

	base_path = template_to_base_path(output, google_songs)
	filepaths = [base_path]

	if include_paths:
		filepaths.extend(include_paths)

	local_songs = get_local_songs(
		filepaths, max_depth=max_depth,
		include_filters=include_filter, all_includes=all_includes,
		exclude_filters=exclude_filter, all_excludes=all_excludes
	)

	logger.info("Comparing song collections")
	to_download = list(
		gm_utils.find_missing_items(
			google_songs, local_songs, fields=['artist', 'album', 'title', 'tracknumber'], normalize_values=True
		)
	)
	to_download.sort(key=lambda song: (song.get('artist'), song.get('album'), song.get('track_number')))

	if not to_download:
		logger.info("No songs to download")
	elif dry_run:
		logger.info(f"Found {len(to_download)} songs to download")

		if logger.level <= 10:
			for song in to_download:
				title = song.get('title', "<title>")
				artist = song.get('artist', "<artist>")
				album = song.get('album', "<album>")
				song_id = song['id']

				logger.debug(f"{title} -- {artist} -- {album} ({song_id})")
	else:
		download_songs(mm, to_download, template=output)

	mm.logout()
	logger.info("All done!")


@sync.command('up')
@click.version_option(__version__, '-V', '--version', prog_name=__title__, message="%(prog)s %(version)s")
@click.option('-l', '--log', is_flag=True, default=False, help="Log to file.")
@click.option('-v', '--verbose', count=True)
@click.option('-q', '--quiet', count=True)
@click.option('-n', '--dry-run', is_flag=True, default=False, help="Output list of songs that would be uploaded.")
@click.option(
	'-u', '--username', metavar='USERNAME', default='',
	help="Your Google username or e-mail address.\nUsed to separate saved credentials."
)
@click.option(
	'--uploader-id', metavar='ID',
	help="A unique id given as a MAC address (e.g. '00:11:22:33:AA:BB').\nThis should only be provided when the default does not work."
)
@click.option(
	'--no-recursion', is_flag=True, default=False,
	help="Disable recursion when scanning for local files.\nRecursion is enabled by default."
)
@click.option(
	'--max-depth', metavar='DEPTH', type=int,
	help="Set maximum depth of recursion when scanning for local files.\nDefault is infinite recursion."
)
@click.option(
	'-f', '--include-filter', metavar='FILTER', multiple=True, callback=split_filter_strings,
	help="Metadata filters to match Google songs.\nSongs can match any filter criteria."
)
@click.option(
	'-fa', '--all-includes', is_flag=True, default=False,
	help="Songs must match all include filter criteria to be included."
)
@click.option(
	'-F', '--exclude-filter', metavar='FILTER', multiple=True, callback=split_filter_strings,
	help="Metadata filters to match Google songs.\nSongs can match any filter criteria."
)
@click.option(
	'-Fa', '--all-excludes', is_flag=True, default=False,
	help="Songs must match all exclude filter criteria to be included."
)
@click.option('--delete-on-success', is_flag=True, default=False, help="Delete successfully uploaded local files.")
@click.option(
	'--transcode-lossless/--no-transcode-lossless', is_flag=True, default=True,
	help="Transcode lossless files to MP3 for upload."
)
@click.option(
	'--transcode-lossy/--no-transcode-lossy', is_flag=True, default=True,
	help="Transcode non-MP3 lossy files to MP3 for upload."
)
@click.argument('input-paths', nargs=-1, type=CustomPath(resolve_path=True), callback=default_to_cwd)
def sync_up(
	log, verbose, quiet, dry_run, username, uploader_id, no_recursion, max_depth, delete_on_success,
	transcode_lossless, transcode_lossy, include_filter, all_includes, exclude_filter, all_excludes, input_paths):
	"""Sync songs to a Google Music library."""

	configure_logging(verbose - quiet, log_to_file=log)

	logger.info("Logging in to Google Music")
	mm = google_music.musicmanager(username, uploader_id=uploader_id)

	if not mm.is_authenticated:
		sys.exit("Failed to authenticate client.")

	if no_recursion:
		max_depth = 0
	elif max_depth is None:
		max_depth = float('inf')

	google_songs = filter_songs(
		mm.songs(),
		include_filters=include_filter, all_includes=all_includes,
		exclude_filters=exclude_filter, all_excludes=all_excludes
	)

	local_songs = get_local_songs(
		input_paths, max_depth=max_depth,
		include_filters=include_filter, all_includes=all_includes,
		exclude_filters=exclude_filter, all_excludes=all_excludes
	)

	logger.info("Comparing song collections")
	to_upload = sorted(
		gm_utils.find_missing_items(
			local_songs, google_songs, fields=['artist', 'album', 'title', 'tracknumber'], normalize_values=True
		)
	)

	if not to_upload:
		logger.info("No songs to upload")
	elif dry_run:
		logger.info(f"Found {len(to_upload)} songs to upload")

		if logger.level <= 10:
			for song in to_upload:
				logger.debug(song)
	else:
		upload_songs(
			mm, to_upload, transcode_lossless=transcode_lossless,
			transcode_lossy=transcode_lossy, delete_on_success=delete_on_success
		)

	mm.logout()
	logger.info("All done!")