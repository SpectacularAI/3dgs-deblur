"""Process raw synthetic input data to the main benchmark format"""
import os
import json
import shutil
import cv2
import numpy as np

POSE_POSITION_NOISE_REL = 0.05
POSE_ORIENTATION_NOISE_DEG = 1

INTRINSIC_NOISE_REL = 0.01

def rotation_matrix_to_rotvec(R):
    # Using a proven/stable algorithm. Other options are sketchy for small rotation
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(R).as_rotvec()

def quaternion_to_rotation_matrix(q_wxyz):
    q = q_wxyz
    return np.array([
        [q[0]*q[0]+q[1]*q[1]-q[2]*q[2]-q[3]*q[3], 2*q[1]*q[2] - 2*q[0]*q[3], 2*q[1]*q[3] + 2*q[0]*q[2]],
        [2*q[1]*q[2] + 2*q[0]*q[3], q[0]*q[0] - q[1]*q[1] + q[2]*q[2] - q[3]*q[3], 2*q[2]*q[3] - 2*q[0]*q[1]],
        [2*q[1]*q[3] - 2*q[0]*q[2], 2*q[2]*q[3] + 2*q[0]*q[1], q[0]*q[0] - q[1]*q[1] - q[2]*q[2] + q[3]*q[3]]
    ])

def deterministic_uniform_rand_generator(seed=1000):
    """
    A simple pseudorandom number generator that returns the
    same random sequence on all machines. The quality of these
    random numbers is low but this is fine for this particular
    application.
    """

    # see https://en.cppreference.com/w/cpp/numeric/random/linear_congruential_engine

    a, c, m = 48271, 0, 2147483647
    x = seed + 1
    uniform_steps = 999

    while True:
        x = (a * x + c) % m
        yield float(x % uniform_steps) / uniform_steps

def process(data_path, target, noisy_poses=False, noisy_intrinsics=False):
    """
    # --- Based on
    # https://github.com/limacv/Deblur-NeRF/blob/766ca3cfafa026ea45f75ee1d3186ec3d9e13d99/scripts/synthe2poses.py
    # and used under the following license

    MIT License

    Copyright (c) 2020 bmild

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """

    print(f"Processing: {data_path} -> {target}")
    if os.path.exists(target): shutil.rmtree(target)

    input_path = data_path
    json_path = os.path.join(input_path, "transforms.json")
    out_path = os.path.join(target, "images")
    converted_json_path = os.path.join(target, "transforms.json")
    os.makedirs(out_path, exist_ok=True)

    rand = deterministic_uniform_rand_generator()
    def rand3():
        nonlocal rand
        return np.array([next(rand) for _ in range(3)]) * 2 - 1

    def convert_pose_c2w(pose, scaling):
        pose = np.array(pose)
        pose[:3, :] *= scaling
        return pose

    def get_scaling(m):
        return 1.0 / np.sqrt((m[:3,:3].transpose() @ m[:3,:3])[0,0])

    with open(json_path, 'r') as metaf:
        meta = json.load(metaf)
        frames_data = meta["frames"]
        fov = meta["fov"]
        h, w = meta['h'], meta['w']
        exposure_time = meta["exposure_time"]
        rolling_shutter_time = meta["rolling_shutter_time"]

    focal_length = w / 2 / np.tan(fov / 2)

    if noisy_intrinsics:
        # slight (fixed) error in intrinsics
        intrinsic_noisy_scaling_x = 1 + INTRINSIC_NOISE_REL
        intrinsic_noisy_scaling_y = 1 - INTRINSIC_NOISE_REL
    else:
        intrinsic_noisy_scaling_x = 1
        intrinsic_noisy_scaling_y = 1

    converted_meta = {
        "aabb_scale": 16,
        "w": w,
        "h": h,
        "cx": w/2,
        "cy": h/2,
        "orientation_override": "none",
        "exposure_time": exposure_time,
        "rolling_shutter_time": rolling_shutter_time,
        "fl_x": focal_length * intrinsic_noisy_scaling_x,
        "fl_y": focal_length * intrinsic_noisy_scaling_y,
        "k1": 0,
        "k2": 0,
        "p1": 0,
        "p2": 0,
        "frames": []
    }

    scaling = None

    cam_positions = []

    for frame_data in frames_data:
        pose = np.array(frame_data["transform_matrix"])
        if scaling is None:
            scaling = get_scaling(pose)
        pose = convert_pose_c2w(pose, scaling)
        cam_positions.append(pose[:3, 3])
        img_path = os.path.join(data_path, frame_data["filename"])
        img_name = os.path.basename(img_path)
        img_out = os.path.join(out_path, img_name)

        if frame_data["blurcount"] == 0:
            img = cv2.imread(img_path)
            cv2.imwrite(img_out, img)

            velocity_cam = np.array([0, 0, 0])
            ang_vel_cam = np.array([0, 0, 0])
        else:
            img = cv2.imread(img_path)
            blur_poses = []
            for bluri in range(frame_data["blurcount"]):
                blur_poses.append(convert_pose_c2w(frame_data['blur_matrices'][bluri], scaling))

            velocity_w = (blur_poses[-1][:3, 3] - blur_poses[0][:3, 3]) / (exposure_time + rolling_shutter_time)
            rot = blur_poses[-1][:3, :3] @ blur_poses[0][:3, :3].transpose()
            rot_vec = rotation_matrix_to_rotvec(rot)
            # print(rot, rot_vec, np.linalg.norm(rot_vec))
            ang_vel_w = rot_vec / (exposure_time + rolling_shutter_time)

            R_w2c = pose[:3, :3].transpose()
            velocity_cam = R_w2c @ velocity_w
            ang_vel_cam = R_w2c @ ang_vel_w
            # print(velocity_cam, ang_vel_cam)
            cv2.imwrite(img_out, img)

        print(f"frame {img_name} saved!")

        converted_meta["frames"].append({
            "camera_linear_velocity": velocity_cam.tolist(),
            "camera_angular_velocity": ang_vel_cam.tolist(),
            "file_path": f"./images/{img_name}",
            "transform_matrix": pose.tolist()
        })
    
    if noisy_poses:
        center = np.mean(cam_positions, axis=0)
        scene_motion_scale = np.max(np.linalg.norm(cam_positions - center, axis=1))
        pos_noise_scale = POSE_POSITION_NOISE_REL * scene_motion_scale
        print('center point of scene cameras %s scale %g, pose noise scale +-%g' % (
            str(center.tolist()),
            scene_motion_scale,
            pos_noise_scale))
        for f in converted_meta['frames']:
            pose = np.array(f['transform_matrix'])
            pose[:3, 3] + rand3() * pos_noise_scale
            noise_ang = 0
            while noise_ang < 1e-6:
                noise_rot_vec = rand3() * POSE_ORIENTATION_NOISE_DEG / 180.0 * np.pi
                noise_ang = np.linalg.norm(noise_rot_vec)

            noise_rot_dir = noise_rot_vec / noise_ang
            noise_quat = [np.cos(noise_ang*0.5)] + (np.sin(noise_ang*0.5) * noise_rot_dir).tolist()
            noise_R = quaternion_to_rotation_matrix(noise_quat)
            pose[:3, :3] = pose[:3, :3] @ noise_R
            f['transform_matrix'] = pose.tolist()

    with open(converted_json_path, 'wt') as f:
        json.dump(converted_meta, f, indent=4)

def point_cloud_to_ply(xyzrgbs, out_fn):
    with open(out_fn, 'wt') as f:
        f.write('\n'.join([
            'ply',
            'format ascii 1.0',
            'element vertex %d' % len(xyzrgbs),
            'property float x',
            'property float y',
            'property float z',
            'property uint8 red',
            'property uint8 green',
            'property uint8 blue',
            'end_header'
        ]) + '\n')
        for r in xyzrgbs:
            for i in range(3): r[i+3] = int(r[i+3])
            f.write(' '.join([str(v) for v in r]) + '\n')

def triangulate_point(o1, d1, o2, d2):
    A = np.stack([d1, -d2]).T
    b = o2 - o1
    x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    P1 = o1 + x[0] * d1
    P2 = o2 + x[1] * d2
    P = (P1 + P2) / 2
    return P

def reproject_point(p, c2w, intrinsics):
    p_cam = c2w[:3, :3].transpose() @ (p - c2w[:3, 3])
    MIN_D = 1e-6

    if -p_cam[2] <= MIN_D: return None

    p_img = p_cam[:2] / -p_cam[2]
    p_px = [p_img[0] * intrinsics['fl_x'] + intrinsics['cx'], -p_img[1] * intrinsics['fl_y'] + intrinsics['cy']]
    return p_px

def reprojection_error(p_reproj, p_orig):
    if p_reproj is None: return 1e6
    return np.linalg.norm(p_reproj - np.array(p_orig))

def triangulate(points1, points2, c2w_i, c2w_j, matches, intrinsics, reprojection_error_pixels):
    filtered_matches = []
    points3d = []
    rejected_matches = []

    for match in matches:
        i, j = match.queryIdx, match.trainIdx

        def to_dir(p):
            px = (p[0] - intrinsics['cx']) / intrinsics['fl_x']
            py = -(p[1] - intrinsics['cy']) / intrinsics['fl_y']
            h = [px, py, -1]
            return np.array(h) / np.linalg.norm(h)

        p1 = points1[i].pt
        p2 = points2[j].pt

        dir_i_cam = to_dir(p1)
        dir_j_cam = to_dir(p2)

        dir_i = c2w_i[:3, :3] @ dir_i_cam
        dir_j = c2w_j[:3, :3] @ dir_j_cam

        P = triangulate_point(c2w_i[:3, 3], dir_i, c2w_j[:3, 3], dir_j)

        rp1 = reproject_point(P, c2w_i, intrinsics)
        rp2 = reproject_point(P, c2w_j, intrinsics)

        err = max(
            reprojection_error(rp1, p1),
            reprojection_error(rp2, p2))

        if err > reprojection_error_pixels:
            rejected_matches.append((match, rp1, rp2))
            continue

        filtered_matches.append(match)
        points3d.append(P)

    return filtered_matches, points3d, rejected_matches

def generate_seed_points_match_and_triangulate(target, visualize=False, dry_run=False, reprojection_error_pixels=10):
    json_path = os.path.join(target, "transforms.json")
    def is_eval_frame(i, frame):
        if i % 8 == 0:
            if 'camera_linear_velocity' in frame:
                vel = np.linalg.norm(frame['camera_linear_velocity']) + np.linalg.norm(frame['camera_angular_velocity'])
                assert(vel == 0)
            return True
        return False

    with open(json_path, 'rt') as f: transforms = json.load(f)
    training_frames = [f for i, f in enumerate(sorted(transforms['frames'], key=lambda fr: fr['file_path'])) if not is_eval_frame(i, f)]

    transforms['ply_file_path'] = './sparse_pc.ply'
    converted_json = transforms

    images = [cv2.imread(os.path.join(target, frame['file_path'])) for frame in training_frames]

    # --- By ChatGPT
    def find_keypoints_and_descriptors(images, detector):
        """Find keypoints and descriptors for each image using the given detector."""
        keypoints_and_descriptors = []
        for image in images:
            keypoints, descriptors = detector.detectAndCompute(image, None)
            keypoints_and_descriptors.append((keypoints, descriptors))
        return keypoints_and_descriptors

    def match_descriptors_and_triangulate(descriptor_pairs, matcher, frames, intrinsics):
        """Match descriptors between all pairs of images."""
        matches = {}
        n = len(descriptor_pairs)
        for i in range(n):
            for j in range(i+1, n):
                matches_ij = matcher.match(descriptor_pairs[i][1], descriptor_pairs[j][1])
                matches_ij = sorted(matches_ij, key=lambda x: x.distance)

                c2w_i = np.array(frames[i]['transform_matrix'])
                c2w_j = np.array(frames[j]['transform_matrix'])

                matches_ij, points3d, rejected_matches = triangulate(
                    descriptor_pairs[i][0],
                    descriptor_pairs[j][0],
                    c2w_i, c2w_j,
                    matches_ij, intrinsics, reprojection_error_pixels)
                matches[(i, j)] = (matches_ij, points3d, rejected_matches)

        return matches

    def visualize_matches(images, keypoints_and_descriptors, matches, pair):
        """Visualize the matches for a specific pair of images."""
        img1, img2 = images[pair[0]], images[pair[1]]
        kp1, kp2 = keypoints_and_descriptors[pair[0]][0], keypoints_and_descriptors[pair[1]][0]
        matches_ij, points, rejected_matches = matches[pair]
        img_matches = cv2.drawMatches(img1, kp1, img2, kp2, matches_ij, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        for rm in rejected_matches:
            match, rp1, rp2 = rm
            p1_orig = tuple(map(int, kp1[match.queryIdx].pt))
            p2_orig_x, p2_orig_y = tuple(map(int, kp2[match.trainIdx].pt))
            p2_orig_x += img1.shape[1]
            p2_orig = (p2_orig_x, p2_orig_y)
            cv2.circle(img_matches, p1_orig, 3, (0, 0, 255), 1)
            cv2.circle(img_matches, p2_orig, 3, (0, 0, 255), 1)
            if rp1 is not None:
                cv2.line(img_matches, p1_orig, tuple(map(int, rp1)), (0, 0, 255), 1)
            if rp2 is not None:
                rp2_x, rp2_y = tuple(map(int, rp2))
                cv2.line(img_matches, p2_orig, (rp2_x + img1.shape[1], rp2_y), (0, 0, 255), 1)
        cv2.imshow(f"Matches between image {pair[0]} and {pair[1]}", img_matches)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    detector = cv2.SIFT_create()
    print('finding keypoints and descriptors...')
    keypoints_and_descriptors = find_keypoints_and_descriptors(images, detector)
    print('matching descriptors...')
    #bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    bf_matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
    matches = match_descriptors_and_triangulate(keypoints_and_descriptors, bf_matcher, training_frames, transforms)
    if visualize:
        visualize_matches(images, keypoints_and_descriptors, matches, (0, 1))

    xyzrgbs = []
    for i in range(len(images)):
        for j in range(i+1, len(images)):
            matches_ij, points, rejected_matches = matches[(i, j)]
            for (k, match) in enumerate(matches_ij):
                p = points[k]
                kp1 = keypoints_and_descriptors[i][0][match.queryIdx].pt
                color = images[i][int(kp1[1]), int(kp1[0]), [2, 1, 0]]
                xyzrgbs.append(p.tolist() + color.tolist())
    print('Triangulated %d points' % len(xyzrgbs))

    if not dry_run:
        with open(json_path, 'wt') as f:
            json.dump(converted_json, f, indent=4)

        seed_ply_path = os.path.join(target, "sparse_pc.ply")
        point_cloud_to_ply(xyzrgbs, seed_ply_path)

def process_dataset_folder(
        base_folder, 
        output_folder,
        subfolder,
        points_only=False,
        noisy_poses=False,
        noisy_intrinsics=False,
        dry_run=False,
        visualize=False):
    items = os.listdir(base_folder)
    directories = sorted([item for item in items if os.path.isdir(os.path.join(base_folder, item))])

    for directory in directories:
        print(directory)
        full_path = os.path.join(base_folder, directory, subfolder)
        if not os.path.exists(full_path): continue
        out_path = os.path.join(output_folder, directory)
        if not points_only and not dry_run:
            process(full_path, out_path, noisy_poses=noisy_poses, noisy_intrinsics=noisy_intrinsics)
        if os.path.exists(out_path):
            generate_seed_points_match_and_triangulate(out_path, visualize=visualize)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--dry_run', action='store_true')
    parser.add_argument('--points_only', action='store_true')
    parser.add_argument('--visualize', action='store_true')
    args = parser.parse_args()

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-posenoise',
        subfolder='raw_clear',
        noisy_poses=True,
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-rs',
        subfolder='raw_rs',
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-mb',
        subfolder='raw_mb',
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-mb-posenoise',
        subfolder='raw_mb',
        noisy_poses=True,
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-clear',
        subfolder='raw_clear',
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-mbrs',
        subfolder='raw_mbrs',
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-mbrs-posenoise',
        subfolder='raw_mbrs',
        noisy_poses=True,
        **vars(args))

    process_dataset_folder(
        'data/inputs-raw/synthetic-raw',
        'data/inputs-processed/synthetic-mbrs-pose-calib-noise',
        subfolder='raw_mbrs',
        noisy_poses=True,
        noisy_intrinsics=True,
        **vars(args))