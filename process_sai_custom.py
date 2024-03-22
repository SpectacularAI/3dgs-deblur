"""Process a single custom SAI input"""
import os
import subprocess
import shutil
import json
import tempfile

from process_sai_inputs import SAI_CLI_PROCESS_PARAMS

DEFAULT_OUT_FOLDER = 'data/inputs-processed/custom'

def ensure_exposure_time(target, input_folder):
    trans_fn = os.path.join(target, 'transforms.json')
    with open(trans_fn) as f:
        transforms = json.load(f)
    
    if 'exposure_time' in transforms: return

    with open(os.path.join(input_folder, 'data.jsonl')) as f:
        for line in f:
            d = json.loads(line)
            if 'frames' in d:
                e = d['frames'][0].get('exposureTimeSeconds', None)
                if e is not None:
                    print('got exposure time %g from data.jsonl' % e)
                    transforms['exposure_time'] = e
                    with open(trans_fn, 'wt') as f:
                        json.dump(transforms, f, indent=4)
                    return
    
    raise RuntimeError("no exposure time available")

def process(args):
    def maybe_run_cmd(cmd):
        print('COMMAND:', cmd)
        if not args.dry_run: subprocess.check_call(cmd)

    def maybe_unzip(fn):
        name = os.path.basename(fn)
        if name.endswith('.zip'):
            name = name[:-4]
            tempdir = tempfile.mkdtemp()
            input_folder = os.path.join(tempdir, 'recording')
            extract_command = [
                "unzip",
                fn,
                "-d",
                input_folder,
            ]
            maybe_run_cmd(extract_command)
            if not args.dry_run:
                # handle folder inside zip
                for f in os.listdir(input_folder):
                    if f == name:
                        input_folder = os.path.join(input_folder, f)
                        break
        else:
            input_folder = fn
        
        return name, input_folder

    sai_params = json.loads(json.dumps(SAI_CLI_PROCESS_PARAMS))
    sai_params['key_frame_distance'] = args.key_frame_distance

    tempdir = None
    name, input_folder = maybe_unzip(args.spectacular_rec_input_folder_or_zip)

    sai_params_list = []
    for k, v in sai_params.items():
        if k == 'internal':
            for k2, v2 in v.items():
                sai_params_list.append(f'--{k}={k2}:{v2}')
        else:
            if v is None:
                sai_params_list.append(f'--{k}')
            else:
                sai_params_list.append(f'--{k}={v}')
        
    result_name = name

    if args.output_folder is None:
        final_target = os.path.join(DEFAULT_OUT_FOLDER, result_name)
    else:
        final_target = args.output_folder

    if not args.skip_colmap:
        if tempdir is None: tempdir = tempfile.mkdtemp()
        target = os.path.join(tempdir, 'sai-cli', result_name)
    else:
        target = final_target

    cmd = [
        'sai-cli', 'process',
        input_folder,
        target
    ] + sai_params_list

    if args.preview:
        cmd.extend(['--preview', '--preview3d'])

    if os.path.exists(target): shutil.rmtree(target)
    maybe_run_cmd(cmd)
    if not args.dry_run: ensure_exposure_time(target, input_folder)

    if not args.skip_colmap:
        colmap_target = os.path.join(tempdir, 'colmap-sai-cli-imgs', result_name)
        colmap_cmd = [
            'python', 'run_colmap.py',
            target,
            colmap_target
        ]
        maybe_run_cmd(colmap_cmd)
        
        combine_cmd = [
            'python', 'combine.py',
            colmap_target,
            target,
            final_target,
            '--tolerate_missing'
        ]
        if args.keep_intrinsics:
            combine_cmd.append('--keep_intrinsics')
        
        if os.path.exists(final_target): shutil.rmtree(final_target)
        maybe_run_cmd(combine_cmd)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spectacular_rec_input_folder_or_zip", type=str)
    parser.add_argument("output_folder", type=str, default=None, nargs='?')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--skip_colmap', action='store_true')
    parser.add_argument('--keep_intrinsics', action='store_true')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--key_frame_distance', type=float, default=0.1,
        help="Minimum key frame distance in meters, default (0.1), increase for larger scenes")
    args = parser.parse_args()

    process(args)
