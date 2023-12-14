#!/bin/bash
blender_path="/root/blender-3.6.5-linux-x64/blender"
objs=(chair_specular_point drums_specular_point ficus_specular_point hotdog_specular_point lego_specular_point materials_specular_point mic_specular_point ship_specular_point)
gpus=(0 1 2 3 4 5 6 7)

# root_path="/root/autodl-tmp/gaussian-splatting/blender/hotdog_LightOrigin"
root_path="/root/autodl-tmp/gaussian-splatting/blender"
image_path="${root_path}/images"
video_path="${root_path}/video"

tmux_name=directional_light_render
cur_idx=0

for obj in "${objs[@]}"; do
    ((cur_idx=cur_idx+1))
    echo "${cur_idx}, ${obj}"
    cd "point_light/${obj}" || exit 1
    export CUDA_VISIBLE_DEVICES=${gpus[cur_idx-1]}

    "${blender_path}" --background --factory-startup main.blend --python ../../360_view_point_train.py -- "${root_path}"
    python ../../image2video.py "${image_path}" "${video_path}" 
done