"""Combine COLMAP poses with sai-cli velocities"""
import os
import json
import shutil

def process(input_folder, args):
    if args.override_calibration is None:
        override_calibration = None
    else:
        with open(args.override_calibration, 'rt') as f:
            calib_json = json.load(f)
        calib_json_cam0, = calib_json['cameras']
        override_calibration = calib_json_cam0
    
    name = os.path.basename(os.path.normpath(input_folder))
    print('name', name)
    SAI_INPUT_ROOT = 'data/inputs-processed/' + args.dataset

    def read_json(path):
        with open(path) as f:
            return json.load(f)

    if args.sai_input_folder is None:
        sai_folder = os.path.join(SAI_INPUT_ROOT, name)
    else:
        sai_folder = args.sai_input_folder

    if args.pose_opt_pass_dir is None:
        src_poses = read_json(os.path.join(input_folder, 'transforms.json'))
        image_folder = os.path.join(input_folder, 'images')
        ply_pc = os.path.join(input_folder, 'sparse_pc.ply')
    else:
        model_f = os.path.join(input_folder, args.model_name)
        input_json_path =  os.path.join(model_f, os.listdir(model_f)[0], 'transforms_train.json')
        src_poses = { 'frames': read_json(input_json_path) }
        image_folder = os.path.join(sai_folder, 'images')
        ply_pc = os.path.join(sai_folder, 'sparse_pc.ply')

    sai_poses = read_json(os.path.join(sai_folder, 'transforms.json'))

    src_poses_by_filename = { './images/' + os.path.basename(f['file_path']): f for f in src_poses['frames'] }
    if len(src_poses_by_filename) == 0:
        print('skipping: no source poses found')
        return

    # print([(k, src_poses_by_filename[k]['file_path']) for k in sorted(src_poses_by_filename.keys())])

    combined_frames = []

    import numpy as np
    frame_centers_sai = []
    frame_centers_src = []

    for sai_frame in sai_poses['frames']:
        id = sai_frame['file_path']
        if id.startswith('images'): id = './' + id
        frame = src_poses_by_filename.get(id, None)

        if frame is None:
            print('warning: could not find source pose for %s, skipping' % id)
            if not args.tolerate_missing: return
            continue
        # print('found frame', id)
        
        if 'transform' in frame:
            frame['transform_matrix'] = frame['transform']
            frame['transform_matrix'].append([0, 0, 0, 1])
            del frame['transform']

        frame['file_path'] = id

        frame_centers_sai.append(np.array(sai_frame['transform_matrix'])[:3, 3].tolist())
        frame_centers_src.append(np.array(frame['transform_matrix'])[:3, 3].tolist())

        for prop in ['camera_angular_velocity', 'camera_linear_velocity']:
            if prop in sai_frame:
                frame[prop] = sai_frame[prop]

        for prop in ['motion_blur_score']:
            if prop in sai_frame:
                frame[prop] = sai_frame[prop]

        for prop in ['colmap_im_id']:
            if prop in frame:
                del frame[prop]

        combined_frames.append(frame)

    # scale velocities to match COLMAP
    frame_centers_sai = np.array(frame_centers_sai)
    frame_centers_src = np.array(frame_centers_src)
    frame_centers_sai -= np.mean(frame_centers_sai, axis=0)
    frame_centers_src -= np.mean(frame_centers_src, axis=0)
    scale_factor = np.sqrt(np.sum(frame_centers_src**2)) / np.sqrt(np.sum(frame_centers_sai**2))
    print('scene scale factor %.12f' % scale_factor)
    if args.pose_opt_pass_dir is None: 
        print('scaling linear velocities')

        for frame in combined_frames:
            # only linear velocity should be scaled
            frame['camera_linear_velocity'] = [v * scale_factor for v in frame['camera_linear_velocity']]
    
    processed_prefix = 'data/inputs-processed'
    
    if args.pose_opt_pass_dir is not None:
        output_prefix = os.path.join(processed_prefix, args.dataset + '-2nd-pass')
        combined_poses = sai_poses

    elif args.keep_intrinsics or override_calibration is not None:
        combined_poses = sai_poses

        if override_calibration is not None:
            assert(override_calibration['model'] == 'brown-conrady')
            def write_to_calib(names, values):
                for i, n in enumerate(names):
                    combined_poses[n] = values[i]

            write_to_calib('k1 k2 p1 p2 k3'.split(), override_calibration['distortionCoefficients'][:5])
            write_to_calib('fl_x fl_y cx cy'.split(),  [override_calibration[c] for c in 'focalLengthX focalLengthY principalPointX principalPointY'.split()])

        if override_calibration is None and args.set_rolling_shutter_to is None:
            intrinsics_postfix = 'orig'
        else:
            intrinsics_postfix = 'calib'

        output_prefix = os.path.join(processed_prefix, 'colmap-' + args.dataset + '-' + intrinsics_postfix + '-intrinsics')
        combined_poses['applied_transform'] = src_poses['applied_transform']

        for prop in ['orientation_override', 'auto_scale_poses_override', 'fx', 'fy']:
            if prop in combined_poses:
                del combined_poses[prop]
    else:
        output_prefix = os.path.join(processed_prefix, 'colmap-' + args.dataset + '-vels')
        combined_poses = src_poses
        for prop in ['exposure_time', 'rolling_shutter_time']:
            if prop in sai_poses:
                combined_poses[prop] = sai_poses[prop]

    combined_poses['frames'] = combined_frames
    if args.set_rolling_shutter_to is not None:
        combined_poses['rolling_shutter_time'] = args.set_rolling_shutter_to

    if args.output_folder is None:
        output_folder = os.path.join(output_prefix, name)
    else:
        output_folder = args.output_folder

    print('Output folder: ' + output_folder)
    if not args.dry_run:
        if os.path.exists(output_folder): shutil.rmtree(output_folder)
        shutil.copytree(image_folder, os.path.join(output_folder, 'images'))
        # shutil.copytree(colmap_folder, os.path.join(output_folder, 'colmap'))
        shutil.copyfile(ply_pc, os.path.join(output_folder, 'sparse_pc.ply'))
        with open (os.path.join(output_folder, 'transforms.json'), 'w') as f:
            json.dump(combined_poses, f, indent=4)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument('sai_input_folder', default=None, nargs='?')
    parser.add_argument('output_folder', default=None, nargs='?')
    parser.add_argument('--dataset', default='sai-cli')
    parser.add_argument('--set_rolling_shutter_to', default=None, type=float)
    parser.add_argument('--keep_intrinsics', action='store_true')
    parser.add_argument('--tolerate_missing', action='store_true')
    parser.add_argument('--override_calibration', type=str, default=None)
    parser.add_argument('--pose_opt_pass_dir', type=str, default=None)
    parser.add_argument('--model_name', default='splatfacto')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--case_number', type=int, default=-1)
    args = parser.parse_args()

    if args.input_folder in ['all']:
        args.case_number = 0
        args.input_folder = None

    selected_cases = []

    if args.input_folder is None:
        if args.pose_opt_pass_dir is None:
            src_folder = 'data/inputs-processed/colmap-' + args.dataset + '-imgs'
        else:
            src_folder = args.pose_opt_pass_dir

        cases = [os.path.join(src_folder, f) for f in sorted(os.listdir(src_folder))]

        if args.case_number == -1:
            print('valid cases')
            for i, c in enumerate(cases): print(str(i+1) + ':\t' + c)
        elif args.case_number == 0:
            selected_cases = cases
        else:
            selected_cases = [cases[args.case_number - 1]]
    else:
        selected_cases = [args.input_folder]

    for case in selected_cases:
        print('Processing ' + case)
        process(case, args)
