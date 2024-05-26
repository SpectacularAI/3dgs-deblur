"""Generate demo video camera trajectory"""
import os
import json
import subprocess
import numpy as np

class SplineInterpolator:        
    def __init__(self, target, frames_per_transition):
        self.target = target
        self.positions = []
        self.orientations = []
        self.loop = False
        self.tension = 0.0
        self.model_frame = None
        self.frames_per_transition = frames_per_transition

    def push(self, frame):
        from scipy.spatial.transform import Rotation
        m = np.array(frame['camera_to_world'])
        self.positions.append(m[:3, 3].tolist())
        q_xyzw = Rotation.from_matrix(m[:3, :3]).as_quat().tolist()
        self.orientations.append(q_xyzw)
        if self.model_frame is None:
            self.model_frame = frame

    def finish(self):
        import splines
        import splines.quaternion
        from scipy.spatial.transform import Rotation

        # as in Nerfstudio
        end_cond = "closed" if self.loop else "natural"

        orientation_spline = splines.quaternion.KochanekBartels(
            [
                splines.quaternion.UnitQuaternion.from_unit_xyzw(q)
                for q in self.orientations
            ],
            tcb=(self.tension, 0.0, 0.0),
            endconditions=end_cond,
        )

        position_spline = splines.KochanekBartels(
            self.positions,
            tcb=(self.tension, 0.0, 0.0),
            endconditions=end_cond,
        )

        n = len(self.positions)
        for t in np.linspace(0, n-1, num=(n-1)*self.frames_per_transition, endpoint=True):
            f = { k: v for k, v in self.model_frame.items() }

            q = orientation_spline.evaluate(t)
            p = position_spline.evaluate(t)
            m = np.eye(4)
            m[:3, 3] = p
            m[:3, :3] = Rotation.from_quat([*q.vector, q.scalar]).as_matrix()

            f['camera_to_world'] = m.tolist()
            self.target.append(f)

def look_at(cam_pos, cam_target, up_dir=np.array([0, 0, 1])):
    z = cam_target - cam_pos
    z = z / np.linalg.norm(z)
    x = np.cross(z, up_dir)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    y = y / np.linalg.norm(y)
    m = np.eye(4)
    m[:3, 3] = cam_pos
    m[:3, :3] = np.column_stack((x, -y, -z))
    return m

def get_original_length_seconds(raw_input_data_jsonl):
    with open(raw_input_data_jsonl, 'rt') as f:
        first_ts = None
        for line in f:
            d = json.loads(line)
            if 'time' in d:
                last_ts = d['time']
                if first_ts is None:
                    first_ts = last_ts
    return last_ts - first_ts

def add_velocities(camera_path, loop=False):
    from scipy.spatial.transform import Rotation

    path = camera_path['camera_path']
    for i in range(len(path)):
        if loop:
            i_prev = (i - 1) % len(path)
            i_next = (i + 1) % len(path)
        else:
            i_prev = max(0, i - 1)
            i_next = min(len(path) - 1, i + 1)
        
        delta_t = i_next - i_prev

        prev_pose = np.array(path[i_prev]['camera_to_world'])
        next_pose = np.array(path[i_next]['camera_to_world'])

        velocity_w = (next_pose[:3, 3] - prev_pose[:3, 3]) / delta_t

        cur_pose = np.array(path[i]['camera_to_world'])

        rot = next_pose[:3, :3] @ prev_pose[:3, :3].transpose()
        rot_vec = Rotation.from_matrix(rot).as_rotvec()
        ang_vel_w = rot_vec / delta_t

        R_w2c = cur_pose[:3, :3].transpose()
        velocity_cam = R_w2c @ velocity_w
        ang_vel_cam = R_w2c @ ang_vel_w

        path[i]['camera_linear_velocity'] = velocity_cam.tolist()
        path[i]['camera_angular_velocity'] = ang_vel_cam.tolist()

def process(out_folder, args):
    import numpy as np

    path = os.path.normpath(out_folder)
    name = os.path.basename(path)
    variant_folder = os.path.split(path)[0]
    # variant = os.path.basename(variant_folder)
    dataset_folder = os.path.split(variant_folder)[0]
    dataset = os.path.basename(dataset_folder)
    result_folder = os.path.join(out_folder, 'splatfacto', os.listdir(os.path.join(out_folder, 'splatfacto'))[0])
    config_file = os.path.join(result_folder, 'config.yml')

    input_folder = os.path.join('data/inputs-processed', dataset, name)

    with open(os.path.join(input_folder, 'transforms.json'), 'rt') as f:
        transforms = json.load(f)

    with open(os.path.join(result_folder, 'dataparser_transforms.json'), 'rt') as f:
        parser_transforms = json.load(f)

    def transform_func(m):
        if 'applied_transform' in transforms:
            M1 = np.array(transforms['applied_transform'] + [[0,0,0,1]])
        else:
            M1 = np.eye(4)
        M = np.array(parser_transforms['transform'] + [[0,0,0,1]])

        m = np.array(m)
        M = M @ np.linalg.inv(M1)
        m = M @ m
        m[:3, 3] *= parser_transforms['scale']
        return m

    if args.original_trajectory:        
        raw_input_data_jsonl = os.path.join('data', 'inputs-raw', 'spectacular-rec', name, 'data.jsonl')
        
        if os.path.exists(raw_input_data_jsonl):
            length_seconds = get_original_length_seconds(raw_input_data_jsonl)
            print('original length %g' % length_seconds)
        else:
            length_seconds = len(transforms['frames']) * 0.3
            print('approx. length %g' % length_seconds)

        length_seconds /= args.playback_speed
        
        def get_frame_number(frame):
            return int(frame['file_path'].rpartition('_')[-1].split('.')[0])
        
        frames = sorted(transforms['frames'], key=get_frame_number)
        frames = frames[::args.key_frame_stride]

        if args.max_duration is not None:
            max_frames = round(args.max_duration / length_seconds * len(frames))
            if max_frames < len(frames):
                length_seconds = length_seconds * max_frames / len(frames)
                print('keeping %d/%d key frames to cut duration to %g' % (max_frames, len(frames), length_seconds))
                frames = frames[:max_frames]

        frame_poses = [transform_func(frame['transform_matrix']) for frame in frames]
        loop = False
    else:
        length_seconds = args.artificial_length_seconds
        loop = True

        rough_up_dir = np.array([0, 0, 1])

        frame_poses_np = [transform_func(frame['transform_matrix']) for frame in transforms['frames']]
        scene_cam_center = np.mean([m[:3, 3] for m in frame_poses_np], axis=0)
        scene_cam_mean_dir = np.mean([-m[:3, 2] for m in frame_poses_np], axis=0)
        scene_cam_mean_dir = scene_cam_mean_dir / np.linalg.norm(scene_cam_mean_dir)

        scene_scale = np.max([np.linalg.norm(m[:3, 3] - scene_cam_center) for m in frame_poses_np])
        cam_target = scene_cam_center + scene_cam_mean_dir * scene_scale * args.artificial_relative_look_at_distance
        left = np.cross(rough_up_dir, scene_cam_mean_dir)
        left = left / np.linalg.norm(left)
        up = np.cross(scene_cam_mean_dir, left)

        up_dim = np.max(np.abs(np.dot([m[:3, 3] - scene_cam_center for m in frame_poses_np], up)))
        left_dim = np.max(np.abs(np.dot([m[:3, 3] - scene_cam_center for m in frame_poses_np], left)))
        
        frame_poses = []
        for t in np.linspace(0, 2*np.pi, endpoint=False, num=100):
            frame_poses.append(look_at(
                scene_cam_center + args.artificial_relative_motion_scale * (
                    up_dim * up * np.sin(t * args.artificial_y_rounds) +
                    left_dim * left * np.cos(t)
                ),
                cam_target,
                rough_up_dir
            ))

        center_cam_to_world = look_at(scene_cam_center, cam_target, rough_up_dir)

    fov = 2.0 * np.arctan(0.5 * transforms['h'] / transforms['fl_y']) / np.pi * 180.0 / args.zoom
    frames_per_transition = round((length_seconds *  args.fps) / (len(frame_poses) - 1))

    width = transforms['w']
    height = transforms['h']
    if args.resolution is not None:
        width, height = [int(x) for x in args.resolution.split('x')]

    aspect = width / float(height)

    cam_path = {
        'render_width': width,
        'render_height': height,
        'fps': args.fps,
        'seconds': length_seconds,
        'camera_path': []
    }
                
    interpolator = SplineInterpolator(cam_path['camera_path'], frames_per_transition=frames_per_transition)
    interpolator.loop = loop

    for pose in frame_poses:
        # print(frame['file_path'])
        interpolator.push({
            'aspect': aspect,
            'fov': fov,
            'camera_to_world': pose
        })

    interpolator.finish()

    add_velocities(cam_path)
    cam_path['rolling_shutter_time'] = args.rolling_shutter_time
    cam_path['exposure_time'] = args.exposure_time

    if args.artificial_keep_center_pose:
        for c in cam_path['camera_path']: c['camera_to_world'] = center_cam_to_world.tolist()

    trajectory_file = os.path.join(result_folder, 'demo_video_camera_path.json')

    if args.output_video_file is None:
        video_fn = ['demo_video']
        if args.rolling_shutter_time > 0:
            video_fn.append('rs')
        if args.exposure_time > 0:
            video_fn.append('mb')
        
        video_file = os.path.join(result_folder, '-'.join(video_fn) + '.mp4')
    else:
        video_file = args.output_video_file

    render_cmd = [
        'ns-render',
        'camera-path',
        '--load-config', config_file,
        '--camera-path-filename', trajectory_file,
        '--output-path', video_file
    ]

    if args.video_crf is not None:
        render_cmd.extend(['--crf', str(args.video_crf)])

    if not args.dry_run:
        with open(trajectory_file, 'wt') as f:
            json.dump(cam_path, f, indent=4)

        subprocess.check_call(render_cmd)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("input_folder", type=str, default=None, nargs='?')
    parser.add_argument('--output_variant_folder', default='data/outputs/colmap-sai-cli-imgs/baseline', type=str)
    parser.add_argument('-o', '--output_video_file', default=None, type=str)
    parser.add_argument('--key_frame_stride', default=3, type=int)
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--original_trajectory', action='store_true')
    parser.add_argument('--fps', default=30, type=int)
    parser.add_argument('--playback_speed', default=0.5, type=float)
    parser.add_argument('--artificial_relative_motion_scale', default=0.6, type=float)
    parser.add_argument('--artificial_relative_look_at_distance', default=3, type=float)
    parser.add_argument('--artificial_y_rounds', default=1, type=int)
    parser.add_argument('--artificial_length_seconds', default=8, type=float)
    parser.add_argument('--artificial_keep_center_pose', action='store_true')
    parser.add_argument('--rolling_shutter_time', default=0.0, type=float)
    parser.add_argument('--max_duration', default=None, type=float)
    parser.add_argument('--resolution', type=str, default=None)
    parser.add_argument('--exposure_time', default=0.0, type=float)
    parser.add_argument('--zoom', default=1.0, type=float)
    parser.add_argument('--video_crf', default=None, type=int)
    parser.add_argument('--case_number', type=int, default=-1)
    args = parser.parse_args()

    if args.input_folder in ['all']:
        args.case_number = 0
        args.input_folder = None

    selected_cases = []

    if args.input_folder is None:
        src_folder = args.output_variant_folder
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
