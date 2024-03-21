"""Process raw input data to the main benchmark format"""
import os
import subprocess
import shutil
import json

SAI_CLI_PROCESS_PARAMS = {
    'image_format': 'png',
    'no_undistort': None,
    'key_frame_distance': 0.1,
    'internal': {
        'maxKeypoints': 2000,
        'optimizerMaxIterations': 50,
    }
}

DATASET_SPECIFIC_PARAMETERS = {}

def process_subfolders(spec, output_folder, method='sai', only_this_case_number=None, dry_run=False, preview=False):
    def process(folder, counter, prefix, named):
        if named:
            name = os.path.basename(folder)
        else:
            name = "%02d" % counter
        
        if prefix is not None:
            name = prefix + '-' + name

        sai_params = json.loads(json.dumps(SAI_CLI_PROCESS_PARAMS)) # deep copy
        out_dataset_folder = output_folder
        if args.no_blur_score_filter:
            out_dataset_folder += '-no-blur-select'
            sai_params['blur_filter_range'] = 0
            sai_params['internal']['keyFrameCandidateSelectionBufferSize'] = 1

        for k, v in DATASET_SPECIFIC_PARAMETERS.get(prefix, {}).items():
            if k == 'internal':
                for k2, v2 in v.items():
                    sai_params['internal'][k2] = v2
            else:
                sai_params[k] = v

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
            
        target = os.path.join(out_dataset_folder, name.replace('_', '-').replace('-capture', ''))

        if method == 'sai':
            cmd = [
                'sai-cli', 'process',
                folder,
                target
            ] + sai_params_list

            if preview:
                cmd.extend(['--preview', '--preview3d'])

        elif method == 'colmap-video':
            [
                'ns-process-data',
                'video',
                '--data', os.path.join(folder, 'data.mp4'),
                '--output-dir', target
            ]
        else:
            assert(False)

        if dry_run:
            print(cmd)
            return
        print(f"Processing: {folder} -> {target}")

        if os.path.exists(target): shutil.rmtree(target)
        subprocess.check_call(cmd)

    counter = 1
    for (base_folder, prefix, named) in spec:
        items = os.listdir(base_folder)
        directories = sorted([item for item in items if os.path.isdir(os.path.join(base_folder, item))])

        dir_counter = 1
        # Loop through each directory and run a command
        for directory in directories:
            full_path = os.path.join(base_folder, directory)
            if only_this_case_number is None or only_this_case_number == counter:
                print('case %d: %s' % (counter, full_path))
                process(full_path, dir_counter, prefix, named)
            counter += 1
            dir_counter += 1

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case_number", type=int, default=None)
    parser.add_argument('--method', choices={'sai', 'colmap-video'}, default='sai')
    parser.add_argument('--no_blur_score_filter', action='store_true')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--dry_run', action='store_true')
    args = parser.parse_args()

    if args.method == 'sai':
        out_folder ='data/inputs-processed/sai-cli'
    elif args.method == 'colmap-video':
        out_folder ='data/inputs-processed/colmap-video'
    else:
        assert(False)

    process_subfolders([
            ('data/inputs-raw/spectacular-rec', None, True),
        ],
        out_folder,
        method=args.method,
        only_this_case_number=args.case_number,
        dry_run=args.dry_run,
        preview=args.preview)
