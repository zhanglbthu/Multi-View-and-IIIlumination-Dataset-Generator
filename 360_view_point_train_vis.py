# A simple script that uses blender to render views of a single object by rotation the camera around it.
# Also produces depth map at the same time.

import argparse, sys, os
import json
import bpy
import mathutils
import numpy as np
         
DEBUG = False
            
VIEWS = 16
RESOLUTION = 800
RESULTS_PATH = 'train'
DEPTH_SCALE = 1.4
COLOR_DEPTH = 32
FORMAT = 'OPEN_EXR'
RANDOM_VIEWS = True
FIX_VIEWS = True
UPPER_VIEWS = True
RANDOM_CAMERA = True
LIGHT_TYPE = 'POINT'


fp = bpy.path.abspath(f"//{RESULTS_PATH}")

def enable_cuda():
    ## this function if borrowed from https://github.com/nytimes/rd-blender-docker/issues/3#issuecomment-618459326
    for scene in bpy.data.scenes:
        scene.cycles.device = 'GPU'

    prefs = bpy.context.preferences
    cprefs = prefs.addons['cycles'].preferences

    # Calling this purges the device list so we need it
    cprefs.refresh_devices()
    # cuda_devices, opencl_devices = cprefs.devices[:2]
    # Attempt to set GPU device types if available
    for compute_device_type in ('CUDA', 'OPENCL'):
        try:
            cprefs.compute_device_type = compute_device_type
            break
        except TypeError:
            pass

    # Enable all CPU and GPU devices
    for device in cprefs.devices:
        device.use = True


def listify_matrix(matrix):
    matrix_list = []
    for row in matrix:
        matrix_list.append(list(row))
    return matrix_list

if not os.path.exists(fp):
    os.makedirs(fp)

enable_cuda()

# Render Optimizations
bpy.context.scene.render.use_persistent_data = True

# Turn off interreflections
bpy.context.scene.cycles.max_bounces = 0

def replace_node_by_diffuse(node_tree, node):
    if len(node.outputs[0].links) == 0:
        return
    links_to_del = []
    to_sockets = []
    for i in range(len(node.outputs[0].links)):
        links_to_del.append(node.outputs[0].links[i])
        to_sockets.append(node.outputs[0].links[i].to_socket)
    for link in links_to_del:
        node_tree.links.remove(link)
    diffuse_node = node_tree.nodes.new('ShaderNodeBsdfDiffuse')
    diffuse_node.inputs[0].default_value = node.inputs[0].default_value
    for to_socket in to_sockets:
        node_tree.links.new(diffuse_node.outputs[0], to_socket)

def recursive_turnoff_specular(node_tree):
    find_bsdf = False
    for node in node_tree.nodes:
        this_bsdf = True
        if isinstance(node, bpy.types.ShaderNodeBsdfPrincipled):
            # node.inputs[7].default_value = 0.0
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeEmission):
            # node.inputs[1].default_value = 0.0
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfDiffuse):
            pass
        elif isinstance(node, bpy.types.ShaderNodeBsdfGlossy):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfGlass):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfAnisotropic):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfTranslucent):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfTransparent):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfVelvet):
            replace_node_by_diffuse(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeGroup):
            this_bsdf = recursive_turnoff_specular(node.node_tree) or this_bsdf
        else:
            this_bsdf = False
        if this_bsdf:
            find_bsdf = True
    return find_bsdf

# Turn off specular effects
for m in bpy.data.materials:
    find_bsdf = recursive_turnoff_specular(m.node_tree)
    if not find_bsdf:
        print(f'Cannot find bsdf {m.name}')

def change_white_color(node_tree, node):
    for link in node.inputs[0].links:
        node_tree.links.remove(link)
    node.inputs[0].default_value = 1.0, 1.0, 1.0, 1.0
    node.inputs[1].default_value = 0.0

def recursive_change_whitecolor(node_tree):
    for node in node_tree.nodes:
        if isinstance(node, bpy.types.ShaderNodeBsdfPrincipled):
            change_white_color(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeBsdfDiffuse):
            change_white_color(node_tree, node)
        elif isinstance(node, bpy.types.ShaderNodeGroup):
            recursive_change_whitecolor(node.node_tree)

# Change all albedos to white
for m in bpy.data.materials:
    recursive_change_whitecolor(m.node_tree)

# Remove all external lights
world_node_tree = bpy.data.worlds['World'].node_tree
world_links = world_node_tree.nodes['World Output'].inputs[0].links
if len(world_links) > 0:
    world_node_tree.links.remove(world_links[0])
world_node_tree.update_tag()

# Set up rendering of depth map.
bpy.context.scene.use_nodes = True
tree = bpy.context.scene.node_tree
links = tree.links

# Add passes for additionally dumping albedo and normals.
#bpy.context.scene.view_layers["RenderLayer"].use_pass_normal = True
bpy.context.scene.render.image_settings.file_format = str(FORMAT)
bpy.context.scene.render.image_settings.color_depth = str(COLOR_DEPTH)

# if not DEBUG:
    # # Create input render layer node.
    # render_layers = tree.nodes.new('CompositorNodeRLayers')

    # depth_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
    # depth_file_output.label = 'Depth Output'
    # if FORMAT == 'OPEN_EXR':
      # links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])
    # else:
      # # Remap as other types can not represent the full range of depth.
      # map = tree.nodes.new(type="CompositorNodeMapValue")
      # # Size is chosen kind of arbitrarily, try out until you're satisfied with resulting depth map.
      # map.offset = [-0.7]
      # map.size = [DEPTH_SCALE]
      # map.use_min = True
      # map.min = [0]
      # links.new(render_layers.outputs['Depth'], map.inputs[0])

      # links.new(map.outputs[0], depth_file_output.inputs[0])

    # normal_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
    # normal_file_output.label = 'Normal Output'
    # links.new(render_layers.outputs['Normal'], normal_file_output.inputs[0])

# Background
bpy.context.scene.render.dither_intensity = 0.0
bpy.context.scene.render.film_transparent = True

# Create collection for objects not to render with background

objs = [ob for ob in bpy.context.scene.objects if (ob.type in ('EMPTY') and 'Empty' in ob.name) or 'Sun' in ob.name]
if FIX_VIEWS:
    objs = [ob for ob in objs if ob.name != 'Empty']
bpy.ops.object.delete({"selected_objects": objs})

def parent_obj_to_camera(name, b_camera):
    origin = (0, 0, 0)
    b_empty = bpy.data.objects.new(name, None)
    b_empty.location = origin
    b_camera.parent = b_empty  # setup parenting

    bpy.context.collection.objects.link(b_empty)
    bpy.context.view_layer.objects.active = b_empty
    return b_empty


scene = bpy.context.scene
scene.render.resolution_x = RESOLUTION
scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100

cam = scene.objects['Camera']
if not FIX_VIEWS:
    cam.location = (0, 4.0, 0.5)
    cam_constraint = cam.constraints.new(type='TRACK_TO')
    cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    cam_constraint.up_axis = 'UP_Y'
    b_empty = parent_obj_to_camera('Empty', cam)
    cam_constraint.target = b_empty

sun_data = bpy.data.lights.new(name='Sun', type=LIGHT_TYPE)
sun_data.cycles.max_bounces = 0
if LIGHT_TYPE == 'SUN':
    sun_data.energy = 1.5
    sun_data.angle = 0
elif LIGHT_TYPE == 'POINT':
    sun_data.energy = 15000
    sun_data.shadow_soft_size = 0
sun_light = bpy.data.objects.new(name='Sun', object_data=sun_data)
bpy.context.collection.objects.link(sun_light)
bpy.context.view_layer.objects.active = sun_light
sun_light.location = (0, 2.0, 1.0)
p_empty = parent_obj_to_camera('Empty_light', sun_light)
light_constraint = sun_light.constraints.new(type='TRACK_TO')
light_constraint.track_axis = 'TRACK_NEGATIVE_Z'
light_constraint.up_axis = 'UP_Y'
light_constraint.target = p_empty


scene.render.image_settings.file_format = 'PNG'  # set output format to .png

from math import radians

stepsize = 360.0 / VIEWS
rotation_mode = 'XYZ'

# if not DEBUG:
    # for output_node in [depth_file_output, normal_file_output]:
        # output_node.base_path = ''

in_data = json.load(open(fp + '/../' + f'transforms_{RESULTS_PATH}.json'))

original_cam_matrix = cam.matrix_world.copy()
original_sun_light = sun_light.matrix_world.copy()

for i in range(0, len(in_data['frames'])):
    this_data = in_data['frames'][i]

    if not FIX_VIEWS:
        # b_empty.rotation_euler = R.from_matrix((np.array(this_data['transform_matrix']) @ np.linalg.inv(original_cam_matrix))[:3, :3]).as_euler('xyz').tolist()
        cam.matrix_world = np.array(this_data['transform_matrix']).T

    
    # p_empty.rotation_euler = R.from_matrix(np.linalg.inv((np.linalg.inv(original_sun_light) @ np.array(this_data['transform_matrix_sun']))[:3, :3])).as_euler('xyz').tolist()
    sun_light.matrix_world = np.array(this_data['transform_matrix_sun']).T
    scene.render.filepath = this_data['file_path'] + '_white_'

    if DEBUG:
        break
    else:
        bpy.ops.render.render(write_still=True)  # render still
    
    # img = cv2.imread(this_data['file_path'] + '_white_.png')
    # img[img != 0] = 255
    # cv2.imwrite(this_data['file_path'] + '_white_.png', img)
