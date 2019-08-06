import os
from lib.run_cmd import run_cmd
from colmap_sfm_utils import create_init_files

gpu_index = '-1'


def run_sift_matching(img_dir, db_file, camera_model):
    assert(camera_model == 'PINHOLE' or camera_model == 'PERSPECTIVE')

    if os.path.exists(db_file): # otherwise colmap will skip sift matching
        os.remove(db_file)

    # feature extraction
    cmd = 'colmap feature_extractor --database_path {} \
                                    --image_path {} \
                                    --ImageReader.camera_model {} \
                                    --SiftExtraction.max_image_size 10000  \
                                    --SiftExtraction.estimate_affine_shape 1 \
                                    --SiftExtraction.domain_size_pooling 1\
                                    --SiftExtraction.gpu_index {}'.format(db_file, img_dir, camera_model, gpu_index)
    run_cmd(cmd)

    # feature matching
    cmd = 'colmap exhaustive_matcher --database_path {} \
                                            --SiftMatching.guided_matching 1 \
                                            --SiftMatching.max_error 3 \
                                            --SiftMatching.gpu_index {}'.format(db_file, gpu_index)

    run_cmd(cmd)


def run_point_triangulation(img_dir, db_file, out_dir, template_file, tri_merge_max_reproj_error, tri_complete_max_reproj_error, filter_max_reproj_error):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # create initial poses
    create_init_files(db_file, template_file, out_dir)

    # triangulate points
    cmd = 'colmap point_triangulator --Mapper.ba_refine_principal_point 1 \
                                             --database_path {} \
                                             --image_path {} \
                                             --input_path {} \
                                             --output_path {} \
                                             --Mapper.filter_min_tri_angle 9.999 \
                                             --Mapper.init_max_forward_motion 1e20 \
                                             --Mapper.tri_min_angle 10 \
                                             --Mapper.tri_merge_max_reproj_error {} \
                                             --Mapper.tri_complete_max_reproj_error {} \
                                             --Mapper.filter_max_reproj_error {} \
                                             --Mapper.extract_colors 1 \
                                             --Mapper.ba_refine_focal_length 0 \
                                             --Mapper.ba_refine_extra_params 0\
                                             --Mapper.max_extra_param 1e20 \
                                             --Mapper.ba_local_num_images 6 \
                                             --Mapper.ba_local_max_num_iterations 100 \
                                             --Mapper.ba_global_images_ratio 1.0000001\
                                             --Mapper.ba_global_max_num_iterations 100 \
                                             --Mapper.tri_ignore_two_view_tracks 0'.format(db_file, img_dir, out_dir, out_dir,
                                                                                               tri_merge_max_reproj_error,
                                                                                               tri_complete_max_reproj_error,
                                                                                               filter_max_reproj_error)
    run_cmd(cmd)


def run_global_ba(in_dir, out_dir, weight):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # global bundle adjustment
    # one meter is roughly three pixels, we should square it
    cmd = 'colmap bundle_adjuster --input_path {in_dir} --output_path {out_dir} \
                                    --BundleAdjustment.max_num_iterations 5000 \
                                    --BundleAdjustment.refine_focal_length 0\
                                    --BundleAdjustment.refine_principal_point 1 \
                                    --BundleAdjustment.refine_extra_params 0 \
                                    --BundleAdjustment.refine_extrinsics 0 \
                                    --BundleAdjustment.function_tolerance 1e-6 \
                                    --BundleAdjustment.gradient_tolerance 1e-8 \
                                    --BundleAdjustment.parameter_tolerance 1e-8 \
                                    --BundleAdjustment.constrain_points 1 \
                                    --BundleAdjustment.constrain_points_loss_weight {weight}'.format(in_dir=in_dir, out_dir=out_dir, weight=weight)

    run_cmd(cmd)

    # cmd = 'colmap bundle_adjuster --input_path {in_dir} --output_path {out_dir} \
    #                                 --BundleAdjustment.max_num_iterations 5000 \
    #                                 --BundleAdjustment.refine_principal_point 1 \
    #                                 --BundleAdjustment.function_tolerance 1e-6 \
    #                                 --BundleAdjustment.gradient_tolerance 1e-8 \
    #                                 --BundleAdjustment.parameter_tolerance 1e-8 \
    #                                 --BundleAdjustment.refine_extra_params 0 \
    #                                 --BundleAdjustment.refine_focal_length 0 \
    #                                 --BundleAdjustment.refine_extrinsics 0\
    #                                 --BundleAdjustment.constrain_points 1 \
    #                                 --BundleAdjustment.constrain_points_loss_weight 1'.format(in_dir=in_dir, out_dir=out_dir)
    # run_cmd(cmd)


# def run_normalize(in_dir, out_dir, tform_file):
#     # normalize sparse reconstruction
#     cmd = 'colmap normalize --input_path {} --output_path {} --save_transform_to_file {}'.format(in_dir, out_dir, tform_file)
#     run_cmd(cmd)
