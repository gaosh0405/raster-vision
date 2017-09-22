from os.path import join
from os import makedirs
from shutil import move
from urllib.parse import urlparse
from subprocess import call

import click

from make_predict_chips import _make_predict_chips
from predict_on_chips import _predict_on_chips
from aggregate_predictions import _aggregate_predictions
from filter_geojson import _filter_geojson
from settings import planet_channel_order

def get_local_path(temp_dir, uri, download=True):
    if uri is None:
        return None

    parsed_uri = urlparse(uri)
    path = parsed_uri.path[1:] if parsed_uri.path[0] == '/' \
        else parsed_uri.path
    if parsed_uri.scheme == 'file':
        path = join(parsed_uri.netloc, path)
    elif parsed_uri.scheme == '':
        path = uri
    elif parsed_uri.scheme == 's3':
        path = join(temp_dir, parsed_uri.netloc, path)
        if download:
            c = ['aws', 's3', 'cp', uri, path]
            print(c)
            call(c)

    return path


def upload_if_needed(src_path, dst_uri):
    if dst_uri is None:
        return

    parsed_uri = urlparse(dst_uri)
    if parsed_uri.scheme == 's3':
        call(['aws', 's3', 'cp', src_path, dst_uri])


@click.command()
@click.argument('inference-graph-uri')
@click.argument('label-map-uri')
@click.argument('image-uri')
@click.argument('agg-predictions-uri')
@click.option('--agg-predictions-debug-uri', default=None)
@click.option('--mask-uri', default=None)
@click.option('--channel-order', nargs=3, type=int,
              default=planet_channel_order)
@click.option('--chip-size', default=300)
@click.pass_context
def run_predict(ctx, inference_graph_uri, label_map_uri, image_uri,
                agg_predictions_uri, agg_predictions_debug_uri, mask_uri,
                channel_order, chip_size):
    """Compute predictions for geospatial imagery."""
    temp_dir = '/opt/data/temp/'
    makedirs(temp_dir, exist_ok=True)
    # TODO clear temp dir

    inference_graph_path = get_local_path(temp_dir, inference_graph_uri)
    label_map_path = get_local_path(temp_dir, label_map_uri)
    # TODO handle VRTs
    image_path = get_local_path(temp_dir, image_uri)
    agg_predictions_path = get_local_path(
        temp_dir, agg_predictions_uri, download=False)
    agg_predictions_debug_path = get_local_path(
            temp_dir, agg_predictions_debug_uri, download=False)
    mask_path = get_local_path(temp_dir, mask_uri)

    chips_dir = join(temp_dir, 'chips')
    chips_info_path = join(temp_dir, 'chips_info.json')
    _make_predict_chips(
        image_path, chips_dir, chips_info_path, chip_size=chip_size,
        channel_order=channel_order)

    predictions_path = join(temp_dir, 'predictions.csv')
    predictions_debug_dir = join(temp_dir, 'predictions_debug')
    _predict_on_chips(inference_graph_path, label_map_path, chips_dir,
                      predictions_path,
                      predictions_debug_dir=predictions_debug_dir)

    _aggregate_predictions(image_path, chips_info_path, predictions_path,
                           label_map_path, agg_predictions_path,
                           agg_predictions_debug_path=agg_predictions_debug_path,
                           channel_order=channel_order)

    if mask_path is not None:
        unfiltered_predictions_path = join(
            temp_dir, 'unfiltered_predictions.geojson')
        move(agg_predictions_path, unfiltered_predictions_path)
        _filter_geojson(
            mask_path, unfiltered_predictions_path, agg_predictions_path)

    upload_if_needed(agg_predictions_path, agg_predictions_uri)
    upload_if_needed(agg_predictions_debug_path, agg_predictions_debug_uri)


if __name__ == '__main__':
    run_predict()
