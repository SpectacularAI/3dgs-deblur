"""Run COLMAP on a single sequence through Nerfstudio scripts"""
import os
import subprocess
import shutil
import tempfile
import json

from process_synthetic_inputs import generate_seed_points_match_and_triangulate

def process(input_folder, args, pass_no=1):

    name = os.path.basename(os.path.normpath(input_folder))

    # 'Wine' is 'Trolley' (see https://github.com/limacv/Deblur-NeRF/issues/39)
    out_name = name.replace('blur', '').replace('2', '').replace('wine', 'trolley')

    test_image_folder = None
    first_pass_folder = None
    input_image_folder = os.path.join(input_folder, 'images_1')

    if args.hloc:
        method = 'hloc'
    else:
        method = 'colmap'

    if args.dataset == 'synthetic_camera_motion_blur':
        paper = 'deblurnerf'
    if args.dataset == 'synthetic_release':
        paper = 'exblurf'
    elif args.dataset == 'nerf_llff_data':
        paper = 'bad-nerf'
    elif args.dataset == 'synthetic-mb':
        input_image_folder = os.path.join(input_folder, 'images')
        paper = 'sai-mb'
    elif args.dataset == 'synthetic-rs':
        input_image_folder = os.path.join(input_folder, 'images')
        paper = 'sai-rs'
    elif args.dataset == 'bad-nerf-gtK-colmap-nvs':
        # this data contains a fixed version of the Tanabata scene
        # where the wine trolley is in the same place in sharp and blurry images
        paper = 'bad-gaussians'
        input_image_folder = os.path.join(input_folder, 'images')
    elif args.dataset == 'colmap-bad-gaussians-synthetic-novel-view-deblurred-training':
        input_image_folder = os.path.join(input_folder, 'images')
        paper = 'mpr-deblurred'

    basename = method + '-' + paper + '-synthetic'

    if pass_no == 1:
        if args.use_all_images:
            dataset_name = basename + '-all'
        else:
            dataset_name = basename + '-novel-view-temp'
    elif pass_no == 2:
        first_pass_folder = os.path.join('data/inputs-processed/' + basename + '-novel-view-temp', out_name)
        dataset_name = basename + '-novel-view'
    elif pass_no == 3:
        dataset_name = basename + '-deblurring'
        input_image_folder = os.path.join(input_folder, 'images')
        test_image_folder = os.path.join(input_folder, 'images_test')
    else:
        assert False

    if pass_no != 1 or args.use_all_images:
        if args.exact_intrinsics:
            dataset_name += '-exact-intrinsics'
        if args.manual_point_cloud:
            dataset_name += '-manual-pc'

    output_folder = os.path.join('data/inputs-processed/' + dataset_name, out_name)

    temp_dir = tempfile.TemporaryDirectory()
    n = 0
    for index, f in enumerate(sorted(os.listdir(input_image_folder))):
        if 'depth' in f: continue
        if not args.dry_run:
            new_name = f
            if test_image_folder is not None:
                new_name = 'train_' + f
            if pass_no == 1 and index % 8 == 0 and not args.use_all_images:
                continue
            shutil.copyfile(os.path.join(input_image_folder, f), os.path.join(temp_dir.name, new_name))
        n += 1
    print('%d images (would be) copied in a temporary directory' % n)

    # Print the path to the temporary directory
    cmd = [
        'ns-process-data',
        'images',
        '--data', temp_dir.name,
        '--output-dir', output_folder,
        '--num-downscales', '1',
        '--matching-method', 'exhaustive',
        '--camera-type', 'simple_pinhole',
    ]

    if args.hloc:
        cmd.extend([
            '--feature-type', 'superpoint',
            '--matcher-type', 'superpoint+lightglue',
        ])

    if not args.post_process_only:
        print(cmd)
        if not args.dry_run:
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            subprocess.check_call(cmd)

    json_fn = os.path.join(output_folder, 'transforms.json')
    if os.path.exists(json_fn):
        with open(json_fn, 'r') as f:
            transforms = json.load(f)
    else:
        transforms = { 'frames': [] }
        assert args.dry_run

    if test_image_folder is not None:
        assert first_pass_folder is None

        test_images = sorted(os.listdir(test_image_folder))
        test_frames = []

        if not any('train_' in f['file_path'] for f in transforms['frames']):
            for index, frame in enumerate(sorted(transforms['frames'], key=lambda x: x['file_path'])):
                orig_fn = test_images[index]
                test_image_fn = 'eval_' + orig_fn
                test_image_path = 'images/' + test_image_fn

                if not args.dry_run:
                    shutil.copyfile(os.path.join(test_image_folder, orig_fn), os.path.join(output_folder, test_image_path))

                if 'train_' not in frame['file_path']:
                    train_path = 'images/train_' + orig_fn
                    if not args.dry_run:
                        shutil.move(os.path.join(output_folder, frame['file_path']), os.path.join(output_folder, train_path))
                    frame['file_path'] = train_path

                test_frame = { k: v for k, v in frame.items() }
                test_frame['file_path'] = test_image_path
                test_frames.append(test_frame)

            transforms['frames'].extend(test_frames)

    elif first_pass_folder is not None:
        with open(os.path.join(first_pass_folder, 'transforms.json'), 'r') as f:
            first_pass_transforms = json.load(f)

        import numpy as np
        to_pose_mat = lambda f : np.array(f['transform_matrix'])
        get_frame_idx = lambda f: int(f['file_path'].split('_')[-1].split('.')[0], base=10) - 1

        train_frame_c2ws = { get_frame_idx(f): to_pose_mat(f) for f in first_pass_transforms['frames'] }
        all_frames_c2ws = { get_frame_idx(f): to_pose_mat(f) for f in transforms['frames'] }

        combined_transforms = { k: v for k, v in first_pass_transforms.items() }
        combined_transforms['frames'] = []

        orig_index = 0
        for index, frame in enumerate(sorted(transforms['frames'], key=lambda x: x['file_path'])):
            #print(frame['file_path'])
            if index % 8 == 0:
                ref_frame = index - 1
                ref_frame_orig_index = orig_index - 1
                if ref_frame < 0:
                    ref_frame = index + 1
                    ref_frame_orig_index = orig_index # the next frame

                # print(index, orig_index, ref_frame, ref_frame_orig_index)

                pose_cur_pred_c2w = train_frame_c2ws[ref_frame_orig_index] @ np.linalg.inv(all_frames_c2ws[ref_frame]) @ all_frames_c2ws[index]
                frame['transform_matrix'] = pose_cur_pred_c2w.tolist()
            else:
                frame['transform_matrix'] = train_frame_c2ws[orig_index].tolist()
                orig_index += 1

            combined_transforms['frames'].append(frame)

        transforms = combined_transforms
        if not args.dry_run:
            shutil.copyfile(os.path.join(first_pass_folder, 'sparse_pc.ply'), os.path.join(output_folder, 'sparse_pc.ply'))

    if args.exact_intrinsics:
        KNOWN_INTRINSICS = {
            "w": 600,
            "h": 400,
            "cx": 300.0,
            "cy": 200.0,
            "fl_x": 541.8502321581475,
            "fl_y": 541.8502321581475,
            "k1": 0,
            "k2": 0,
            "p1": 0,
            "p2": 0,
        }
        for k, v in KNOWN_INTRINSICS.items():
            transforms[k] = v

    print('writing %s' % json_fn)
    if not args.dry_run:
        with open(json_fn, 'wt') as f:
            json.dump(transforms, f, indent=4)

    if pass_no == 1 and args.manual_point_cloud:
        if os.path.exists(output_folder):
            if not args.dry_run:
                backup_ply = os.path.join(output_folder, 'sparse_pc_colmap.ply')
                backup_json = os.path.join(output_folder, 'transforms_colmap.json')
                if not os.path.exists(backup_ply):
                    ply_fn = os.path.join(output_folder, 'sparse_pc.ply')
                    assert os.path.exists(ply_fn) and os.path.exists(json_fn)
                    shutil.copyfile(ply_fn, backup_ply)
                if not os.path.exists(backup_json):
                    shutil.copyfile(json_fn, backup_json)
            generate_seed_points_match_and_triangulate(output_folder, dry_run=args.dry_run, visualize=args.dry_run)
        else:
            assert args.dry_run
    
    temp_dir.cleanup()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--dataset', default='synthetic_camera_motion_blur')
    parser.add_argument('--post_process_only', action='store_true')
    parser.add_argument('--manual_point_cloud', action='store_true')
    parser.add_argument('--deblurring_version', action='store_true')
    parser.add_argument('--exact_intrinsics', action='store_true')
    parser.add_argument('--hloc', action='store_true')
    parser.add_argument('--use_all_images', action='store_true',
                        help='Use both blurry training and sharp test images for training pose registration')
    parser.add_argument('--case_number', type=int, default=-1)
    
    args = parser.parse_args()

    if args.input_folder in ['all']:
        args.case_number = 0
        args.input_folder = None
        
    selected_cases = []
    misc = False

    if args.dataset.endswith('/'): args.dataset = args.dataset[:-1]

    if args.input_folder is None:
        sai_dataset = args.dataset.startswith('synthetic-')

        if sai_dataset:
            input_root = os.path.join('data/inputs-processed/', args.dataset)
        else:
            input_root = os.path.join('data/inputs-raw/', args.dataset)
        cases = [os.path.join(input_root, f)
            for f in sorted(os.listdir(input_root))
            if f.startswith('blur') or sai_dataset or args.dataset == 'colmap-bad-gaussians-synthetic-novel-view-deblurred-training'
        ]

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
        if not args.use_all_images:
            if args.deblurring_version:
                process(case, args, pass_no=3)
            else:
                process(case, args, pass_no=2)
