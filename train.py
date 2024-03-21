"""Train a single instance"""
import os
import subprocess
import shutil
import sys
import time
import datetime
import json
import re

DATASET_SPECIFIC_PARAMETERS = {
    r"synthetic.*": [
        # Splatfacto seems to start to show gaps in reconstruction at high iteration counts
        '--max-num-iterations', '15000',
        # In synthetic data, the blur velocities are accurately known, no need to regularize
        '--pipeline.model.blur-velocity-regularization=0',
        #'--pipeline.model.blur-velocity-regularization=0.1',
    ]
}

def print_cmd(cmd):
    print('RUNNING COMMAND: ' + ' '.join(cmd))

def flags_to_variant_name_and_cmd(args):    
    cmd = []
    variant = []
    if not args.get('no_pose_opt', False):
        variant.append('pose_opt')
        cmd.extend([
            '--pipeline.model.camera-optimizer.mode=SO3xR3',
            '--pipeline.model.use-scale-regularization=True',
            '--pipeline.model.max-gauss-ratio=3',
            '--pipeline.model.sh-degree=0'
        ])

    if not args.get('no_motion_blur', False):
        variant.append('motion_blur')
        cmd.append('--pipeline.model.blur-samples=5')
    else:
        cmd.append('--pipeline.model.blur-samples=0')

    if not args.get('no_rolling_shutter', False):
        variant.append('rolling_shutter')
    else:
        cmd.append('--pipeline.model.rolling-shutter-compensation=False')

    if args.get('train_all', False):
        variant.append('train_all')

    if args.get('no_gamma', False):
        cmd.append('--pipeline.model.gamma=1')
        variant.append('no_gamma')

    if args.get('no_blur_regularization', False):
        cmd.append('--pipeline.model.blur-regularization=0')
        variant.append('no_blur_regularization')

    if args.get('no_blur_velocity_regularization', False):
        cmd.append('--pipeline.model.blur-velocity-regularization=0')
        variant.append('no_blur_velocity_regularization')

    if len(variant) == 0:
        variant.append('baseline')

    return '-'.join(variant), cmd

def compute_manual_scale_factor(transforms_path):
    import numpy as np
    with open(transforms_path) as f:
        data = json.load(f)

    centers = []
    for frame in data['frames']:
        pose = np.array(frame['transform_matrix'])
        centers.append(pose[:3, 3].tolist())
    
    centers = np.array(centers)
    centers = centers - np.mean(centers, axis=0)
    scale_factor = 1.0 / float(np.max(np.abs(centers)))
    return scale_factor

def undo_scale_factor(out_dir_path, scale_factor):
    def undo_scale_factor_file(fn):
        with open(fn) as f:
            data = json.load(f)
        for frame in data:
            for i in range(3):
                frame['transform'][i][3] /= scale_factor
        scaled_fn = fn.rpartition('.')[0] + '_scaled.json'
        print('writing scaled poses to %s' % scaled_fn)
        with open(scaled_fn, 'wt') as f:
            json.dump(data, f, indent=4)

    undo_scale_factor_file(os.path.join(out_dir_path, 'transforms_train.json'))
    undo_scale_factor_file(os.path.join(out_dir_path, 'transforms_eval.json'))

def evaluate(output_folder, elapsed_time, extract_poses=False, dry_run=False, render_images=True, scale_factor=1.0):
    result_paths = find_config_path(output_folder)
    if result_paths is None:
        if dry_run: return
        assert(False)

    out_path, config_path = result_paths
    metrics_path = os.path.join(out_path, 'metrics.json')
    elapsed_time
    eval_cmd = [
        'ns-eval',
         '--load-config', config_path,
         '--output-path', metrics_path
    ]

    print_cmd(eval_cmd)
    if not dry_run:
        subprocess.check_call(eval_cmd)
        with open(metrics_path) as f:
            metrics = json.load(f)
        metrics['wall_clock_time_seconds'] = elapsed_time
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=4)

    if extract_poses:
        extract_poses_cmd = [
            'ns-export',
            'cameras',
            '--load-config', config_path,
            '--output-dir', out_path
        ]
        print_cmd(extract_poses_cmd)
        if not dry_run:
            subprocess.check_call(extract_poses_cmd)
            undo_scale_factor(out_path, scale_factor)
    
    if render_images:
        render_cmd = [
            'python', 'render_model.py',
            '--load-config', config_path
        ]
        print_cmd(render_cmd)
        if not dry_run:
            subprocess.check_call(render_cmd)

def process(input_folder, args):
    name = os.path.split(input_folder)[-1]

    cmd = [
        'ns-train',
        'splatfacto',
        '--data',  input_folder,
        '--viewer.quit-on-train-completion', 'True',
        '--pipeline.model.min-rgb-level', '10',
        # '--logging.local-writer.max-log-size=0'
    ]

    for pattern, values in DATASET_SPECIFIC_PARAMETERS.items():
        if re.match(pattern, args.dataset):
            cmd.extend(values)

    pose_opt_enabled = not args.no_pose_opt

    if '--max-num-iterations' not in cmd:
        if pose_opt_enabled:
            cmd.extend(['--max-num-iterations', '15000'])
        else:
            if args.draft:
                cmd.extend(['--max-num-iterations', '3000'])
            else:
                # 20k is generally nice for real data
                cmd.extend(['--max-num-iterations', '20000'])

    if args.preview:
        cmd.extend([
            '--vis=viewer+tensorboard',
            '--steps-per-eval-all-images', '100'
        ])
    else:
        cmd.append('--vis=tensorboard')

    variant, variant_cmd = flags_to_variant_name_and_cmd(vars(args))
    cmd.extend(variant_cmd)

    if args.case_number is None:
        dataset_folder = 'misc'
    else:
        dataset_folder = args.dataset
        
    variant_folder = os.path.join(dataset_folder, variant)

    output_prefix = 'data/outputs'

    # note: 'name' is automatically added by Nerfstudio
    output_root = os.path.join(output_prefix, variant_folder)

    cmd.extend(['--output-dir', output_root])

    cmd.append('nerfstudio-data')

    manual_scale_factor = 1.0
    if args.train_all:
        manual_scale_factor = compute_manual_scale_factor(os.path.join(input_folder, 'transforms.json'))
        print('manual_scale_factor %g' % manual_scale_factor)

        cmd.extend([
            '--eval-mode', 'all',
            # related to pose optimization when outputs are used
            '--orientation-method', 'none',
            '--center-method', 'none',
            '--scale-factor', str(manual_scale_factor),
            '--auto-scale-poses', 'False'
        ])
    else:
        if '-scored' in args.input_folder:
            cmd.extend([
                '--eval-mode', 'filename'
            ])
        else:
            cmd.extend([
                '--eval-mode', 'interval',
                '--eval-interval', '8'
            ])

    print_cmd(cmd)
    output_folder = os.path.join(output_root, name)
    elapsed_time = 0
    if not args.dry_run and not args.eval_only:
        if os.path.exists(output_folder) and args.case_number is not None:
            shutil.rmtree(output_folder)

        start_time = time.time()
        subprocess.check_call(cmd)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print('Training time: %s' % str(datetime.timedelta(seconds=elapsed_time)))
    
    evaluate(output_folder, elapsed_time, extract_poses=pose_opt_enabled, dry_run=args.dry_run, scale_factor=manual_scale_factor)

def find_config_path(output_folder):
    model_folder = os.path.join(output_folder, 'splatfacto')
    paths = []
    if os.path.exists(model_folder):
        for subdir in os.listdir(model_folder):
            out_path = os.path.join(model_folder, subdir)
            config_path = os.path.join(out_path, 'config.yml')
            if os.path.exists(config_path):
                paths.append((out_path, config_path))
    if len(paths) == 0: return None
    assert(len(paths) == 1)
    return paths[0]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    baseline = {
        'no_pose_opt',
        'no_motion_blur',
        'no_rolling_shutter'
    }

    no_rolling_shutter_variants = [
        baseline,
        { 'no_rolling_shutter', 'no_pose_opt' },
        { 'no_rolling_shutter', 'no_motion_blur' },
        { 'no_rolling_shutter' }
    ]
    
    full_variants = no_rolling_shutter_variants + [
        { 'no_pose_opt', 'no_motion_blur' },
        { 'no_pose_opt' },
        { 'no_motion_blur' },
        {}
    ]

    default_variants = full_variants

    variants_by_dataset = {
        'synthetic-clear': [
            baseline
        ],
        'synthetic-mb': [
            baseline,
            { 'no_pose_opt', 'no_rolling_shutter' }
        ],
        'synthetic-rs': [
            baseline,
            { 'no_pose_opt', 'no_motion_blur' }
        ],
        'synthetic-posenoise': [
            baseline,
            { 'no_rolling_shutter', 'no_motion_blur' }
        ],
        'synthetic-mbrs': [
            baseline,
            { 'no_pose_opt' },
            { 'no_pose_opt', 'no_motion_blur' },
            { 'no_pose_opt', 'no_rolling_shutter' }
        ],
        #'synthetic-mbrs-posenoise': full_variants,
        #'synthetic-mbrs-pose-calib-noise': full_variants,
        'synthetic-posenoise-2nd-pass': [
            baseline
        ],
        'colmap-sai-cli-vels-blur-scored': [
            baseline,
            { 'no_pose_opt', 'no_rolling_shutter' }
        ]
    }

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument("--preview", action='store_true', help='show Viser preview')
    parser.add_argument("--no_pose_opt", action='store_true')
    parser.add_argument("--no_motion_blur", action='store_true')
    parser.add_argument('--no_rolling_shutter', action='store_true')
    parser.add_argument('--dataset', type=str, default='colmap-sai-cli-vels-blur-scored')
    parser.add_argument('--train_all', action='store_true')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--no_gamma', action='store_true')
    parser.add_argument('--no_blur_regularization', action='store_true')
    parser.add_argument('--no_blur_velocity_regularization', action='store_true')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--eval_only', action='store_true')

    parser.add_argument('--case_number', type=int, default=None)
    args = parser.parse_args()

    if args.input_folder is None and args.case_number is None:
        args.case_number = -1

    if args.case_number is not None:
        INPUT_ROOT = 'data/inputs-processed/' + args.dataset
        sessions = [os.path.join(INPUT_ROOT, f) for f in sorted(os.listdir(INPUT_ROOT))]
        variants = variants_by_dataset.get(args.dataset, default_variants)
        cases = [(s, v) for v in variants for s in sessions]

        if args.case_number <= 0:
            print('valid cases')
            for i, (c, v) in enumerate(cases):
                variant = flags_to_variant_name_and_cmd({k: True for k in v})[0]
                print(str(i+1) + ':\t' + variant + '\t' + c)
            sys.exit(0)
        else:
            args.input_folder, variant = cases[args.case_number - 1]
            for p in variant: setattr(args, p, True)
            print('Running %s %s' % (args.input_folder, str(variant)))

    process(args.input_folder, args)
