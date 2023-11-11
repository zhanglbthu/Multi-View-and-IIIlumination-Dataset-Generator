# blender_path=../../../home/Softwares/blender-3.2.1-linux-x64/blender
blender_path=/root/blender-3.6.5-linux-x64/blender
objs=(chair_specular_point)
gpus=(0)
cur_idx=0
tmux_name=point_light_render

tmux new-session -s ${tmux_name}

for obj in ${objs[@]}; do
    ((cur_idx=cur_idx+1))
    echo ${cur_idx}, ${obj}
    tmux new-window -t ${tmux_name}:${cur_idx} -n ${obj}
    tmux send-keys -t ${tmux_name}:${cur_idx} "cd point_light/${obj}" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "export CUDA_VISIBLE_DEVICES=${gpus[cur_idx-1]}" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "rm -rf train" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "rm -rf normal" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "rm -rf test_one" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "rm -rf floor" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "${blender_path} --background --factory-startup main.blend --python ../360_view_point_train.py" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "${blender_path} --background --factory-startup main.blend --python ../360_view_point_train_vis.py" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "${blender_path} --background --factory-startup main.blend --python ../360_view_test_normal.py" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "${blender_path} --background --factory-startup main.blend --python ../360_view_test_one.py" ENTER
    tmux send-keys -t ${tmux_name}:${cur_idx} "${blender_path} --background --factory-startup main.blend --python ../360_view_test_floor.py" ENTER
done
