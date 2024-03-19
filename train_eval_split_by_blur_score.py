"""Combine COLMAP poses with sai-cli velocities"""
import os
import json
import shutil

def process(input_folder, output_prefix, args):
    name = os.path.basename(os.path.normpath(input_folder))
    print('name', name)

    def read_json(folder):
        with open(os.path.join(folder, 'transforms.json')) as f:
            return json.load(f)

    print(input_folder)
    output_folder = os.path.join(output_prefix, name)

    input_image_folder = os.path.join(input_folder, 'images')
    output_image_folder = os.path.join(output_folder, 'images')
    
    poses = read_json(input_folder)
    poses['frames'].sort(key=lambda x: x['file_path'])

    if not args.dry_run:
        if os.path.exists(output_folder): shutil.rmtree(output_folder)
        os.makedirs(output_image_folder)
        
    ival_start = 0
    while ival_start < len(poses['frames']):
        ival_end = ival_start + args.interval
        least_blur = sorted(poses['frames'][ival_start:ival_end], key=lambda x: x['motion_blur_score'])[0]['file_path']

        for frame in poses['frames'][ival_start:ival_end]:
            id = frame['file_path']
            if id == least_blur:
                new_name = f'eval_' + os.path.basename(id)
            else:
                new_name = f'train_' + os.path.basename(id)

            old_file_name = os.path.join(input_image_folder, os.path.basename(id))
            new_file_name = os.path.join(output_image_folder, new_name)

            frame['file_path'] = os.path.join('images', new_name)
            print("%s -> %s (%g)" % (old_file_name, new_file_name, frame['motion_blur_score']))
            if not args.dry_run:
                shutil.copyfile(old_file_name, new_file_name)

        ival_start = ival_end

    # colmap_folder = os.path.join(args.input_folder, 'colmap')
    ply_pc = os.path.join(input_folder, 'sparse_pc.ply')

    print('Output folder: ' + output_folder)
    if not args.dry_run:
        # shutil.copytree(colmap_folder, os.path.join(output_folder, 'colmap'))
        shutil.copyfile(ply_pc, os.path.join(output_folder, 'sparse_pc.ply'))
        with open (os.path.join(output_folder, 'transforms.json'), 'w') as f:
            json.dump(poses, f, indent=4)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('dataset')
    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument('--interval', type=int, default=8)
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--case_number', type=int, default=-1)
    args = parser.parse_args()

    if args.input_folder in ['all']:
        args.case_number = 0
        args.input_folder = None

    selected_cases = []

    PROCESSED_PREFIX = 'data/inputs-processed/'
    if args.dataset.startswith(PROCESSED_PREFIX):
        args.dataset = args.dataset[len(PROCESSED_PREFIX):]

    out_folder = os.path.join(PROCESSED_PREFIX, args.dataset + '-blur-scored')

    if args.input_folder is None:
        processed_prefix = os.path.join(PROCESSED_PREFIX, args.dataset)
        cases = [os.path.join(processed_prefix, f) for f in sorted(os.listdir(processed_prefix))]

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
        process(case, out_folder, args)
