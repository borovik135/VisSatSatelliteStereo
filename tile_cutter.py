# cut a big satellite image into small tiles

import os
from lib.rpc_model import RPCModel
from lib.parse_meta import parse_meta
from lib.gen_grid import gen_grid
from lib.check_bbx import check_bbx
from lib.height_range import height_range
from lib.cut_image import cut_image
from lib.tone_map import tone_map
import utm
import json
import numpy as np
import warnings
import copy


class TileCutter(object):
    # dataset_dir here is the cleaned_data_dir
    def __init__(self, dataset_dir, out_dir):
        assert(os.path.exists(out_dir))

        self.dataset_dir = os.path.abspath(dataset_dir)
        self.out_dir = os.path.abspath(out_dir)

        self.ntf_list = []
        self.xml_list = []
        for item in sorted(os.listdir(self.dataset_dir)):
            if item[-4:] == '.NTF':
                xml_file = os.path.join(self.dataset_dir, '{}.XML'.format(item[:-4]))
                self.ntf_list.append(os.path.join(self.dataset_dir, item))
                self.xml_list.append(xml_file)
        self.meta_dicts = [parse_meta(xml_file) for xml_file in self.xml_list]
        self.rpc_models = [RPCModel(meta_dict) for meta_dict in self.meta_dicts]

        self.cnt = len(self.ntf_list)
        # create a ascending date index
        tmp = [(i, self.meta_dicts[i]['capTime']) for i in range(self.cnt)]
        tmp = sorted(tmp, key=lambda x: x[1])
        self.time_index = [x[0] for x in tmp]

        self.min_height, self.max_height = height_range(self.rpc_models)

        print('min_height, max_height: {}, {}'.format(self.min_height, self.max_height))

        # prepare directory structure
        self.image_subdir = os.path.join(self.out_dir, 'images')
        if not os.path.exists(self.image_subdir):
            os.mkdir(self.image_subdir)
        self.metas_subdir = os.path.join(self.out_dir, 'metas')
        if not os.path.exists(self.metas_subdir):
            os.mkdir(self.metas_subdir)
        self.regions_subdir = os.path.join(self.out_dir, 'regions')
        if not os.path.exists(self.regions_subdir):
            os.mkdir(self.regions_subdir)

    # cut area of interest; might divide the aoi into smaller regions
    def cut_aoi(self, zone_number, zone_letter, ul_east, ul_north, lr_east, lr_north):
        # save to aoi_dict
        aoi_dict = {'zone_number': zone_number,
                    'zone_letter': zone_letter,
                    'x': ul_east,
                    'y': ul_north,
                    'w': lr_east - ul_east,
                    'h': ul_north - lr_north}
        with open(os.path.join(self.out_dir, 'aoi_dict.json'), 'w') as fp:
            json.dump(aoi_dict, fp)
        # view the whole aoi as a region
        self.cut_region(zone_number, zone_letter, ul_east, ul_north, lr_east, lr_north)

    def cut_region(self, zone_number, zone_letter, ul_east, ul_north, lr_east, lr_north):
        ul_lat, ul_lon = utm.to_latlon(ul_east, ul_north, zone_number, zone_letter)
        lr_lat, lr_lon = utm.to_latlon(lr_east, lr_north, zone_number, zone_letter)

        lat_points = np.array([ul_lat, lr_lat])
        lon_points = np.array([ul_lon, lr_lon])
        z_points = np.array([self.min_height, self.max_height])
        xx_lat, yy_lon, zz = gen_grid(lat_points, lon_points, z_points)

        # start to process the images
        useful_cnt = 0 # number of useful images
        for k in range(self.cnt):
            print('processing image {}/{}, already collect {} useful images...'.format(k, self.cnt, useful_cnt))
            i = self.time_index[k]   # image index

            # check whether the image is too cloudy
            cloudy_thres = 0.5
            if self.meta_dicts[i]['cloudCover'] > cloudy_thres:
                warnings.warn('discarding this image because of too many clouds, cloudy level: {}, ntf: {}'
                              .format(self.meta_dicts[i]['cloudCover'], self.ntf_list[i]))
                continue

            # compute the bounding box
            col, row = self.rpc_models[i].projection(xx_lat, yy_lon, zz)
            ul_col = int(np.round(np.min(col)))
            ul_row = int(np.round(np.min(row)))
            width = int(np.round(np.max(col))) - ul_col + 1
            height = int(np.round(np.max(row))) - ul_row + 1

            # check whether the bounding box lies in the image
            ntf_width = self.meta_dicts[i]['width']
            ntf_height = self.meta_dicts[i]['height']
            intersect, _, overlap = check_bbx((0, 0, ntf_width, ntf_height),
                                              (ul_col, ul_row, width, height))
            overlap_thres = 0.5
            if overlap < overlap_thres:
                warnings.warn('discarding this image due to small coverage of target area, overlap: {}, ntf: {}'
                              .format(overlap, self.ntf_list[i]))
                continue

            ul_col, ul_row, width, height = intersect

            # cut image
            in_ntf = self.ntf_list[i]
            cap_time = self.meta_dicts[i]['capTime'].strftime("%Y%m%d%H%M%S")
            out_png = os.path.join(self.image_subdir, '{:03d}_{}.png'.format(useful_cnt, cap_time))

            cut_image(in_ntf, out_png, (ntf_width, ntf_height), (ul_col, ul_row, width, height))
            # tone mapping
            tone_map(out_png, out_png)

            # save metadata
            # need to modify the rpc function and image width, height
            meta_dict = copy.deepcopy(self.meta_dicts[i])
            # subtract the cutting offset here
            rpc_dict = meta_dict['rpc']
            rpc_dict['colOff'] = rpc_dict['colOff'] - ul_col
            rpc_dict['rowOff'] = rpc_dict['rowOff'] - ul_row
            meta_dict['rpc'] = rpc_dict
            # modify width, height
            meta_dict['width'] = width
            meta_dict['height'] = height

            with open(os.path.join(self.metas_subdir, '{:03d}_{}.json'.format(useful_cnt, cap_time)), 'w') as fp:
                json.dump(meta_dict, fp, indent=2)

            # save region
            region_dict = {'zone_number': zone_number,
                           'zone_letter': zone_letter,
                           'x': ul_east,
                           'y': ul_north,
                           'w': lr_east - ul_east,
                           'h': ul_north - lr_north}
            with open(os.path.join(self.regions_subdir, '{:03d}_{}.json'.format(useful_cnt, cap_time)), 'w') as fp:
                json.dump(region_dict, fp, indent=2)

            # increase number of useful images
            useful_cnt += 1

            print('\n')