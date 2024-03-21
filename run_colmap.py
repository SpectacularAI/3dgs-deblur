"""Run COLMAP on a single sequence through Nerfstudio scripts"""
import os
import subprocess
import shutil
import tempfile

def process(input_folder, args):
    name = os.path.basename(os.path.normpath(input_folder))
    postf = 'colmap-' + args.dataset + '-imgs'
    if args.output_folder is None:
        output_folder = os.path.join('data/inputs-processed/' + postf, name)
    else:
        output_folder = args.output_folder

    input_image_folder = os.path.join(input_folder, 'images')

    temp_dir = tempfile.TemporaryDirectory()
    n = 0
    for f in os.listdir(input_image_folder):
        if 'depth' in f: continue
        if not args.dry_run:
            shutil.copyfile(os.path.join(input_image_folder, f), os.path.join(temp_dir.name, f))
        n += 1
    print('%d images (would be) copied in a temporary directory' % n)

    # Print the path to the temporary directory
    cmd = [
        'ns-process-data',
        'images',
        '--data', temp_dir.name,
        '--output-dir', output_folder
    ]

    print(cmd)
    if not args.dry_run:
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        subprocess.check_call(cmd)
    
    temp_dir.cleanup()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument("output_folder", type=str, default=None, nargs='?')
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--dataset', default='sai-cli')
    parser.add_argument('--case_number', type=int, default=-1)
    
    args = parser.parse_args()

    if args.input_folder in ['all']:
        args.case_number = 0
        args.input_folder = None
        
    selected_cases = []
    misc = False

    PROCESSED_PREFIX = 'data/inputs-processed/'
    if args.dataset.startswith(PROCESSED_PREFIX):
        args.dataset = args.dataset[len(PROCESSED_PREFIX):]
    if args.dataset.endswith('/'): args.dataset = args.dataset[:-1]

    if args.input_folder is None:
        input_root = os.path.join(PROCESSED_PREFIX, args.dataset)
        cases = [os.path.join(input_root, f) for f in sorted(os.listdir(input_root))]

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
