
import marshal
from math import sin, cos, atan2, pi, degrees, floor, dist
from re import T
pad_h = 252
img_h = 648
img_w = 1152
frame_size = 1152
crop_w = 0
class HandednessAverage:
    def __init__(self):
        self._total_handedness = 0
        self._nb = 0
    def update(self, new_handedness):
        self._total_handedness += new_handedness
        self._nb += 1
        return self._total_handedness / self._nb
    def reset(self):
        self._total_handedness = self._nb = 0
handedness_avg = [HandednessAverage(), HandednessAverage()]
nb_hands_in_previous_frame = 0
single_hand_count = 0
class BufferMgr:
    def __init__(self):
        self._bufs = {}
    def __call__(self, size):
        try:
            buf = self._bufs[size]
        except KeyError:
            buf = self._bufs[size] = Buffer(size)
        return buf
buffer_mgr = BufferMgr()
def send_result(result):
    result_serial = marshal.dumps(result)
    buffer = buffer_mgr(len(result_serial))  
    buffer.getData()[:] = result_serial  
    node.io['host'].send(buffer)
def send_result_no_hand(pd_inf, nb_lm_inf):
    result = [1 if pd_inf else 0, 1 if nb_lm_inf else 0]
    send_result(result)
def send_result_hands(pd_inf, nb_lm_inf, lm_score, handedness, rect_center_x, rect_center_y, rect_size, rotation, rrn_lms, sqn_lms, world_lms, xyz, xyz_zone):
    print(lm_score)
    result = [lm_score, handedness, rect_center_x, rect_center_y, rect_size, rotation, rrn_lms, sqn_lms, world_lms, xyz, xyz_zone]
    send_result(result)
def rr2img(rrn_x, rrn_y):
    X = sqn_rr_center_x + sqn_rr_size * ((rrn_x - 0.5) * cos_rot + (0.5 - rrn_y) * sin_rot)
    Y = sqn_rr_center_y + sqn_rr_size * ((rrn_y - 0.5) * cos_rot + (rrn_x - 0.5) * sin_rot)
    return X, Y
def normalize_radians(angle):
    return angle - 2 * pi * floor((angle + pi) / (2 * pi))
send_new_frame_to_branch = 1
cfg_pre_pd = ImageManipConfig()
cfg_pre_pd.setResizeThumbnail(128, 128, 0, 0, 0)
id_wrist = 0
id_index_mcp = 5
id_middle_mcp = 9
id_ring_mcp =13
ids_for_bounding_box = [0, 1, 2, 3, 5, 6, 9, 10, 13, 14, 17, 18]
lm_input_size = 224
detected_hands = []
while True:
    nb_lm_inf = 0
    if send_new_frame_to_branch == 1: 
        hands = []
        node.io['pre_pd_manip_cfg'].send(cfg_pre_pd)
        detection = node.io['from_post_pd_nn'].get().getLayerFp16("result")
        for i in range(2):
            pd_score, box_x, box_y, box_size, kp0_x, kp0_y, kp2_x, kp2_y = detection[i*8:(i+1)*8]
            if pd_score >= 0.5 and box_size > 0:
                kp02_x = kp2_x - kp0_x
                kp02_y = kp2_y - kp0_y
                sqn_rr_size = 2.9 * box_size
                rotation = 0.5 * pi - atan2(-kp02_y, kp02_x)
                rotation = normalize_radians(rotation)
                sqn_rr_center_x = box_x + 0.5*box_size*sin(rotation)
                sqn_rr_center_y = box_y - 0.5*box_size*cos(rotation)
                hands.append([sqn_rr_size, rotation, sqn_rr_center_x, sqn_rr_center_y])
        if len(hands) == 0:
            send_result_no_hand(True, 0)
            send_new_frame_to_branch = 1
            nb_hands_in_previous_frame = 0
            continue
        if not(nb_hands_in_previous_frame == 1 and len(hands) <= 1):
            detected_hands = hands
        else:
            pass
    last_hand = len(detected_hands) - 1
    for i,hand in enumerate(detected_hands):
        sqn_rr_size, rotation, sqn_rr_center_x, sqn_rr_center_y = hand
        rr = RotatedRect()
        rr.center.x    = sqn_rr_center_x
        rr.center.y    = (sqn_rr_center_y * frame_size - pad_h) / img_h
        rr.size.width  = sqn_rr_size
        rr.size.height = sqn_rr_size * frame_size / img_h
        rr.angle       = degrees(rotation)
        cfg = ImageManipConfig()
        cfg.setCropRotatedRect(rr, True)
        cfg.setResize(lm_input_size, lm_input_size)
        cfg.setReusePreviousImage(False if i == last_hand else True)
        node.io['pre_lm_manip_cfg'].send(cfg)
        nb_lm_inf += 1
    hand_landmarks = dict([("lm_score", []), ("handedness", []), ("rotation", []),
                     ("rect_center_x", []), ("rect_center_y", []), ("rect_size", []), ("rrn_lms", []), ('sqn_lms', []),
                     ("world_lms", []), ("xyz", []), ("xyz_zone", [])])
    updated_detect_hands = []
    for ih, hand in enumerate(detected_hands):
        sqn_rr_size, rotation, sqn_rr_center_x, sqn_rr_center_y = hand
        lm_result = node.io['from_lm_nn'].get()
        lm_score = lm_result.getLayerFp16("Identity_1")[0]
        if lm_score > 0.5:
            handedness = lm_result.getLayerFp16("Identity_2")[0]
            rrn_lms = lm_result.getLayerFp16("Identity_dense/BiasAdd/Add")
            world_lms = 0
            sqn_lms = []
            cos_rot = cos(rotation)
            sin_rot = sin(rotation)
            for i in range(21):
                rrn_lms[3*i] /= lm_input_size
                rrn_lms[3*i+1] /= lm_input_size
                rrn_lms[3*i+2] /= lm_input_size  
                sqn_x, sqn_y = rr2img(rrn_lms[3*i], rrn_lms[3*i+1])
                sqn_lms += [sqn_x, sqn_y]
            xyz = 0
            xyz_zone = 0
            hand_landmarks["lm_score"].append(lm_score)
            hand_landmarks["handedness"].append(handedness)
            hand_landmarks["rotation"].append(rotation)
            hand_landmarks["rect_center_x"].append(sqn_rr_center_x)
            hand_landmarks["rect_center_y"].append(sqn_rr_center_y)
            hand_landmarks["rect_size"].append(sqn_rr_size)
            hand_landmarks["rrn_lms"].append(rrn_lms)
            hand_landmarks["sqn_lms"].append(sqn_lms)
            hand_landmarks["world_lms"].append(world_lms)
            hand_landmarks["xyz"].append(xyz)
            hand_landmarks["xyz_zone"].append(xyz_zone)
            x0 = sqn_lms[0]
            y0 = sqn_lms[1]
            x1 = 0.25 * (sqn_lms[2*id_index_mcp] + sqn_lms[2*id_ring_mcp]) + 0.5 * sqn_lms[2*id_middle_mcp]
            y1 = 0.25 * (sqn_lms[2*id_index_mcp+1] + sqn_lms[2*id_ring_mcp+1]) + 0.5 * sqn_lms[2*id_middle_mcp+1]
            rotation = 0.5 * pi - atan2(y0 - y1, x1 - x0)
            rotation = normalize_radians(rotation)
            min_x = min_y = 1
            max_x = max_y = 0
            for id in ids_for_bounding_box:
                min_x = min(min_x, sqn_lms[2*id])
                max_x = max(max_x, sqn_lms[2*id])
                min_y = min(min_y, sqn_lms[2*id+1])
                max_y = max(max_y, sqn_lms[2*id+1])
            axis_aligned_center_x = 0.5 * (max_x + min_x)
            axis_aligned_center_y = 0.5 * (max_y + min_y)
            cos_rot = cos(rotation)
            sin_rot = sin(rotation)
            min_x = min_y = 1
            max_x = max_y = -1
            for id in ids_for_bounding_box:
                original_x = sqn_lms[2*id] - axis_aligned_center_x
                original_y = sqn_lms[2*id+1] - axis_aligned_center_y
                projected_x = original_x * cos_rot + original_y * sin_rot
                projected_y = -original_x * sin_rot + original_y * cos_rot
                min_x = min(min_x, projected_x)
                max_x = max(max_x, projected_x)
                min_y = min(min_y, projected_y)
                max_y = max(max_y, projected_y)
            projected_center_x = 0.5 * (max_x + min_x)
            projected_center_y = 0.5 * (max_y + min_y)
            center_x = (projected_center_x * cos_rot - projected_center_y * sin_rot + axis_aligned_center_x)
            center_y = (projected_center_x * sin_rot + projected_center_y * cos_rot + axis_aligned_center_y)
            width = (max_x - min_x)
            height = (max_y - min_y)
            sqn_rr_size = 2 * max(width, height) 
            sqn_rr_center_x = (center_x + 0.1 * height * sin_rot) 
            sqn_rr_center_y = (center_y - 0.1 * height * cos_rot) 
            hand[0] = sqn_rr_size
            hand[1] = rotation
            hand[2] = sqn_rr_center_x
            hand[3] = sqn_rr_center_y
            updated_detect_hands.append(hand)
    detected_hands = updated_detect_hands
    if len(detected_hands) == 2: 
        dist_rr_centers = dist([detected_hands[0][2], detected_hands[0][3]], [detected_hands[1][2], detected_hands[1][3]])
        if dist_rr_centers < 0.02:
            if hand_landmarks["lm_score"][0] > hand_landmarks["lm_score"][1]:
                pop_i = 1
            else:
                pop_i = 0
            for k in hand_landmarks:
                hand_landmarks[k].pop(pop_i)
            detected_hands.pop(pop_i)
    nb_hands = len(detected_hands)
    if send_new_frame_to_branch == 1 or nb_hands_in_previous_frame != nb_hands:
        for i in range(2):
            handedness_avg[i].reset()
    for i in range(nb_hands):
        hand_landmarks["handedness"][i] = handedness_avg[i].update(hand_landmarks["handedness"][i])
    if nb_hands == 2 and (hand_landmarks["handedness"][0] - 0.5) * (hand_landmarks["handedness"][1] - 0.5) > 0:
        for k in hand_landmarks:
            hand_landmarks[k].pop(1)
        nb_hands = 1
    if nb_hands == 1:
        single_hand_count += 1
    else:
        single_hand_count = 0
    send_result_hands(send_new_frame_to_branch==1, nb_lm_inf, hand_landmarks["lm_score"], hand_landmarks["handedness"], hand_landmarks["rect_center_x"], hand_landmarks["rect_center_y"], hand_landmarks["rect_size"], hand_landmarks["rotation"], hand_landmarks["rrn_lms"], hand_landmarks["sqn_lms"], hand_landmarks["world_lms"], hand_landmarks["xyz"], hand_landmarks["xyz_zone"])
    if nb_hands == 0:
        send_new_frame_to_branch = 1
    elif nb_hands == 1 and single_hand_count >= 10:
        send_new_frame_to_branch = 1
        single_hand_count = 0
    else:
        send_new_frame_to_branch = 2
    nb_hands_in_previous_frame = nb_hands
    