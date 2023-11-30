#!/bin/bash

blender_path="/root/blender-3.6.5-linux-x64/blender"
objs=("hotdog_specular")
gpus=(0)

cur_idx=0

for obj in "${objs[@]}"; do
    ((cur_idx=cur_idx+1))
    echo "${cur_idx}, ${obj}"
    cd "directional_light/${obj}" || exit 1
    export CUDA_VISIBLE_DEVICES=${gpus[cur_idx-1]}

    rm -rf train
    rm -rf normal
    rm -rf test_one
    rm -rf floor

    "${blender_path}" --background --factory-startup main.blend --python ../../360_view_point_train.py
done