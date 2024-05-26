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
    r".*synthetic.*": [
        # '--max-num-iterations', '20000', # this would be enough, usually
        '--pipeline.model.num-downscales', '0', # low resolution -> no downscaling
        # These help reconstructing large areas with very smooth color,
        # i.e., the synthetic sky. With defaults, large holes can easily appear
        '--pipeline.model.background-color', 'auto',
        '--pipeline.model.cull-scale-thresh', '2.0',
        # Evaluation data is known to be static. Don't try to optimize camera velocities
        '--pipeline.model.optimize-eval-velocities=False',
        # Hight motion blur, needs more samples
        '--pipeline.model.blur-samples=10',
    ]
}

def print_cmd(cmd):
    print('RUNNING COMMAND: ' + ' '.join(cmd))

def flags_to_variant_name_and_cmd(args):    
    cmd = []
    variant = []

    use_gamma_correction = False
    optimize_eval_cameras = False

    if not args.get('no_pose_opt', False):
        optimize_eval_cameras = True
        variant.append('pose_opt')
        cmd.extend([
            '--pipeline.model.camera-optimizer.mode=SO3xR3',
            ## '--pipeline.model.sh-degree=0'
        ])

    if not args.get('no_motion_blur', False):
        variant.append('motion_blur')
        # default blur samples: 5
        use_gamma_correction = not args.get('no_gamma', False)
        if not use_gamma_correction:
            variant.append('no_gamma')
    else:
        cmd.append('--pipeline.model.blur-samples=0')

    if not args.get('no_rolling_shutter', False):
        variant.append('rolling_shutter')
    else:
        cmd.append('--pipeline.model.rolling-shutter-compensation=False')

    if use_gamma_correction:
        # min RGB level only seems necessary with gamma correction
        cmd.append('--pipeline.model.min-rgb-level=10')
    else:
        cmd.append('--pipeline.model.gamma=1')

    if not args.get('no_velocity_opt', False):
        optimize_eval_cameras = True
        cmd.append('--pipeline.model.camera-velocity-optimizer.enabled=True')
        variant.append('velocity_opt')

    if args.get('velocity_opt_zero_init', False):
        cmd.append('--pipeline.model.camera-velocity-optimizer.zero-initial-velocities=True')
        variant.append('zero_init')

    if len(variant) == 0:
        variant.append('baseline')

    return '-'.join(variant), cmd, optimize_eval_cameras

def evaluate(output_folder, elapsed_time, dry_run=False, render_images=True):
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
        '--pipeline.model.rasterize-mode', 'antialiased',
        '--pipeline.model.use-scale-regularization', 'True',
        # '--logging.local-writer.max-log-size=0'
    ]

    for pattern, values in DATASET_SPECIFIC_PARAMETERS.items():
        if re.match(pattern, args.dataset):
            cmd.extend(values)

    if '--max-num-iterations' not in cmd:
        if args.draft:
            cmd.extend(['--max-num-iterations', '3000'])
        else:
            cmd.extend(['--max-num-iterations', '20000'])

    if args.preview:
        cmd.extend([
            '--vis=viewer+tensorboard',
            '--viewer.websocket-host=127.0.0.1'
        ])
    else:
        cmd.append('--vis=tensorboard')

    variant, variant_cmd, optimize_eval_cameras = flags_to_variant_name_and_cmd(vars(args))
    cmd.extend(variant_cmd)

    if args.case_number is None:
        dataset_folder = 'custom'
    else:
        dataset_folder = args.dataset
        
    variant_folder = os.path.join(dataset_folder, variant)

    output_prefix = 'data/outputs'

    # note: 'name' is automatically added by Nerfstudio
    output_root = os.path.join(output_prefix, variant_folder)

    cmd.extend(['--output-dir', output_root])

    cmd.extend([
        'nerfstudio-data',
        '--orientation-method', 'none',
    ])

    if args.train_all:
        cmd.extend([
            '--eval-mode', 'all'
        ])
        optimize_eval_cameras = False
    elif '-scored' in args.input_folder or args.dataset == 'colmap-bad-nerf-synthetic-deblurring':
        cmd.extend([
            '--eval-mode', 'filename'
        ])
    else:
        cmd.extend([
            '--eval-mode', 'interval',
            '--eval-interval', '8'
        ])
        #cmd.extend(['--eval-mode', 'all'])

    if optimize_eval_cameras:
        cmd.extend([
            '--optimize-eval-cameras', 'True',
        ])

    print_cmd(cmd)
    output_folder = os.path.join(output_root, name)
    elapsed_time = 0
    if not args.dry_run and not args.eval_only:
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        start_time = time.time()
        subprocess.check_call(cmd)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print('Training time: %s' % str(datetime.timedelta(seconds=elapsed_time)))
    
    if not args.no_eval:
        evaluate(output_folder, elapsed_time,
            dry_run=args.dry_run,
            render_images=args.render_images)

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

def add_velocity_opt_variants(variants, dataset):
    has_velocity_info = ('sai-' in dataset
        or 'spectacular-rec' in dataset
        or ('synthetic-' in dataset and 'colmap' not in dataset and 'hloc' not in dataset)
    )

    new_variants = []
    for v in variants:
        v1 = v.copy()
        no_velocity_to_optimize = 'no_rolling_shutter' in v and 'no_motion_blur' in v
        if has_velocity_info or no_velocity_to_optimize:
            v1.add('no_velocity_opt')
            new_variants.append(v1)

        if no_velocity_to_optimize: continue

        if has_velocity_info:
            new_variants.append(v)

        v2 = v.copy()
        v2.add('velocity_opt_zero_init')
        new_variants.append(v2)

    return new_variants

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    # note: velocity optimization arguments are auto-added to all of these
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
        set([])
    ]

    default_variants = full_variants
    bad_nerf_variants = [
        baseline,
        { 'no_rolling_shutter', 'no_pose_opt' },
        { 'no_rolling_shutter' }
    ]

    add_popt = lambda a: a + [o - {'no_pose_opt'} for o in a if 'no_pose_opt' in o]

    variants_by_dataset = {
        'synthetic-clear': [
            baseline
        ],
        'synthetic-mb': add_popt([
            baseline,
            { 'no_pose_opt', 'no_rolling_shutter' }
        ]),
        'synthetic-rs': add_popt([
            baseline,
            { 'no_pose_opt', 'no_motion_blur' }
        ]),
        'synthetic-posenoise': add_popt([
            baseline,
            { 'no_rolling_shutter', 'no_motion_blur' }
        ]),
        'synthetic-mbrs': add_popt([
            baseline,
            { 'no_pose_opt' },
            { 'no_pose_opt', 'no_motion_blur' },
            { 'no_pose_opt', 'no_rolling_shutter' }
        ]),
        'synthetic-posenoise-2nd-pass': [
            baseline
        ],
        'colmap-bad-nerf-synthetic-deblurring': bad_nerf_variants,
        'colmap-bad-nerf-synthetic-novel-view': bad_nerf_variants,
        'colmap-bad-nerf-synthetic-novel-view-manual-pc': add_popt(bad_nerf_variants),
        'colmap-exblurf-synthetic-novel-view-manual-pc': bad_nerf_variants,
        'hloc-exblurf-synthetic-novel-view-manual-pc': bad_nerf_variants,
        'hloc-bad-nerf-synthetic-novel-view-manual-pc': bad_nerf_variants,
        'hloc-bad-nerf-synthetic-novel-view-exact-intrinsics-manual-pc': bad_nerf_variants,
        'hloc-bad-gaussians-synthetic-novel-view-manual-pc': bad_nerf_variants,
        'colmap-bad-gaussians-synthetic-novel-view-manual-pc': bad_nerf_variants,
        'colmap-mpr-deblurred-synthetic-all-manual-pc': bad_nerf_variants,
        'colmap-mpr-deblurred-synthetic-novel-view-manual-pc': bad_nerf_variants + [{ 'no_rolling_shutter', 'no_motion_blur' }],
    }

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument("--preview", action='store_true', help='show Viser preview')
    parser.add_argument("--no_pose_opt", action='store_true')
    parser.add_argument("--no_motion_blur", action='store_true')
    parser.add_argument('--no_rolling_shutter', action='store_true')
    parser.add_argument('--no_velocity_opt', action='store_true')
    parser.add_argument('--velocity_opt_zero_init', action='store_true')
    parser.add_argument('--dataset', type=str, default='colmap-sai-cli-vels-blur-scored')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--no_gamma', action='store_true')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--render_images', action='store_true')
    parser.add_argument('--eval_only', action='store_true')
    parser.add_argument('--no_eval', action='store_true')
    parser.add_argument('--train_all', action='store_true')

    parser.add_argument('--case_number', type=int, default=None)
    args = parser.parse_args()

    if args.input_folder is None and args.case_number is None:
        args.case_number = -1

    if args.case_number is not None:
        INPUT_ROOT = 'data/inputs-processed/' + args.dataset
        sessions = [os.path.join(INPUT_ROOT, f) for f in sorted(os.listdir(INPUT_ROOT))]
        variants = add_velocity_opt_variants(variants_by_dataset.get(args.dataset, default_variants), args.dataset)
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
