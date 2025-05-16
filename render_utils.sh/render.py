import bpy
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.view.show_tooltips = False
import json
import math
import os
import argparse
DESIGNER_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

object_name = 'Cube'
object_to_delete = bpy.data.objects.get(object_name)

# Check if the object exists before trying to delete it
if object_to_delete is not None:
    bpy.data.objects.remove(object_to_delete, do_unlink=True)

def import_glb(file_path, object_name):
    bpy.ops.import_scene.gltf(filepath=file_path)
    imported_object = bpy.context.view_layer.objects.active
    if imported_object is not None:
        imported_object.name = object_name

def import_fbx(file_path, object_name):
    bpy.ops.import_scene.fbx(filepath=file_path)
    for obj in bpy.context.selected_objects:
        obj.name = object_name

def create_room(width, depth, height):
    # Create floor
    bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD', location=(0, 0, 0))

    # Extrude to create walls
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, height)})
    bpy.ops.object.mode_set(mode='OBJECT')

    # Scale the walls to the desired dimensions
    bpy.ops.transform.resize(value=(width, depth, 1))

    bpy.context.active_object.location.x += width / 2
    bpy.context.active_object.location.y += depth / 2

def find_files(directory, extensions):
    files = {}
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extensions):
                key = filename.split(".")[0]
                if key not in files:
                    files[key] = os.path.join(root, filename)
    return files

def get_highest_parent_objects():
    highest_parent_objects = []

    for obj in bpy.data.objects:
        # Check if the object has no parent
        if obj.parent is None:
            highest_parent_objects.append(obj)
    return highest_parent_objects

def delete_empty_objects():
    # Iterate through all objects in the scene
    for obj in bpy.context.scene.objects:
        # Check if the object is empty (has no geometry)
        print(obj.name, obj.type)
        if obj.type == 'EMPTY':
            bpy.context.view_layer.objects.active = obj
            bpy.data.objects.remove(obj)

def select_meshes_under_empty(empty_object_name):
    # Get the empty object
    empty_object = bpy.data.objects.get(empty_object_name)
    print(empty_object is not None)
    if empty_object is not None and empty_object.type == 'EMPTY':
        # Iterate through the children of the empty object
        for child in empty_object.children:
            # Check if the child is a mesh
            if child.type == 'MESH':
                # Select the mesh
                child.select_set(True)
                bpy.context.view_layer.objects.active = child
            else:
                select_meshes_under_empty(child.name)

def rescale_object(obj, scale):
    # Ensure the object has a mesh data
    if obj.type == 'MESH':
        bbox_dimensions = obj.dimensions
        scale_factors = (
                         scale["length"] / bbox_dimensions.x, 
                         scale["width"] / bbox_dimensions.y, 
                         scale["height"] / bbox_dimensions.z
                        )
        obj.scale = scale_factors


def setup_scene(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 800

def setup_camera(camera):
    if camera:
        camera.data.type = 'PERSP'
        camera.data.lens = 45
        camera.data.shift_x = 0.49
        camera.data.shift_y = 0.15
        camera.data.clip_start = 1
        camera.data.clip_end = 100

def create_white_material():
    mat = bpy.data.materials.new(name="WhiteFloor")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
    diffuse.inputs[0].default_value = (1, 1, 1, 1)
    output = nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(diffuse.outputs[0], output.inputs[0])
    return mat

def create_floor(mat):

    bpy.ops.mesh.primitive_plane_add(size=5, location=(2.5, 2.5, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=5, location=(2.5, 5, 1.5))
    wall1 = bpy.context.active_object
    wall1.name = "Wall1"
    wall1.rotation_euler = (math.pi/2, 0, 0)
    wall1.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 2.5, 1.5))
    wall2 = bpy.context.active_object
    wall2.name = "Wall2"
    wall2.rotation_euler = (math.pi/2, 0, math.pi/2)
    wall2.data.materials.append(mat)

def rotate_scene(angle_degrees):
    center_x = 2.5
    center_y = 2.5
    angle = math.radians(angle_degrees)
    
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' or obj.name == 'Floor' or obj.name == 'Wall1' or obj.name == 'Wall2':
            pass
        else:
            rel_x = obj.location.x - center_x
            rel_y = obj.location.y - center_y
            
            new_x = center_x + (rel_x * math.cos(angle) - rel_y * math.sin(angle))
            new_y = center_y + (rel_x * math.sin(angle) + rel_y * math.cos(angle))
            
            obj.location.x = new_x
            obj.location.y = new_y
            
            obj.rotation_euler.z += angle

def hide_existing_planes():
    for obj in bpy.data.objects:
        if obj.name.startswith('平面') or obj.name.startswith('plane') or obj.name.startswith('Plane'):
            obj.hide_render = True
            obj.hide_viewport = True





def render_scene(output_path):
    scene = bpy.context.scene
    scene.render.filepath = output_path
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)



def render_blender(answer_json, room_name):
    
    
    objects_in_room = {}
    for item in answer_json:
        if item["new_object_id"] not in ["south_wall", "north_wall", "east_wall", "west_wall", "middle of the room", "ceiling"]:
            objects_in_room[item["new_object_id"]] = item

    directory_path = os.path.join(DESIGNER_PATH, "Assets", room_name)
    fbx_files = find_files(directory_path, ".fbx")
    glb_files = find_files(directory_path, ".glb")

    for item_id, object_in_room in objects_in_room.items():
        if item_id in fbx_files:
            fbx_file_path = fbx_files[item_id]
            import_fbx(fbx_file_path, item_id)

    for item_id, object_in_room in objects_in_room.items():
        if item_id in glb_files:
            glb_file_path = glb_files[item_id]
            import_glb(glb_file_path, item_id)


    parents = get_highest_parent_objects()
    empty_parents = [parent for parent in parents if parent.type == "EMPTY"]
    print(empty_parents)


    for empty_parent in empty_parents:
        bpy.ops.object.select_all(action='DESELECT')
        select_meshes_under_empty(empty_parent.name)
        
        bpy.ops.object.join()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        
        joined_object = bpy.context.view_layer.objects.active
        if joined_object is not None:
            joined_object.name = empty_parent.name + "-joined"

    bpy.context.view_layer.objects.active = None


    MSH_OBJS = [m for m in bpy.context.scene.objects if m.type == 'MESH']
    for OBJS in MSH_OBJS:
        bpy.context.view_layer.objects.active = OBJS
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        OBJS.location = (0.0, 0.0, 0.0)
        bpy.context.view_layer.objects.active = OBJS
        OBJS.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    MSH_OBJS = [m for m in bpy.context.scene.objects if m.type == 'MESH']
    for OBJS in MSH_OBJS:
        item = objects_in_room[OBJS.name.split("-")[0]]
        object_position = (item["position"]["x"], item["position"]["y"], item["position"]["z"])
        object_rotation_z = (item["rotation"]["z_angle"] / 180.0) * math.pi + math.pi
        
        bpy.ops.object.select_all(action='DESELECT')
        OBJS.select_set(True)
        OBJS.location = object_position
        bpy.ops.transform.rotate(value=object_rotation_z, orient_axis='Z')
        rescale_object(OBJS, item["size_in_meters"])


    bpy.ops.object.select_all(action='DESELECT')
    delete_empty_objects()
    create_room(5.0, 5.0, 3.0)


    scene = bpy.context.scene

    camera = bpy.data.objects.get("Camera")

    setup_scene(scene)
    setup_camera(camera)
    
    mat = create_white_material()
    
    hide_existing_planes()
    
    create_floor(mat)
    
    angles = [0, 90, 180, 270]
    for i, angle in enumerate(angles, 1):
        rotate_scene(angle)
        output_path = os.path.join(directory_path, f"{i}.png")
        
        render_scene(output_path)


if __name__ == "__main__":
    # answer_json = json.load(open('/wuhu_uni_ai/limingsheng/rllm/utils/A_bathroom_layout_with_a_modern_style_bathtub_and_a_separate_shower_set_with_a_contemporary_finish_/A_bathroom_layout_with_a_modern_style_bathtub_and_a_separate_shower_set_with_a_contemporary_finish_.json'))
    # room_name = "living_room"

    # render_blender(answer_json, room_name)

    parser = argparse.ArgumentParser(description='Retrieve assets for a room')
    parser.add_argument('--json_file', required=True, help='Path to the answer JSON file')
    parser.add_argument('--room_name', required=True, help='Name of the room')
    args = parser.parse_args()
    
    print("args.room_name", args.room_name)

    answer_json = json.load(open(args.json_file, "r"))


    render_blender(answer_json, args.room_name)
    # render_blender(json.load(open(args.answer_json, "r")), args.room_name)

# python render.py --answer_json /wuhu_uni_ai/limingsheng/rllm/Assets_old/room_312/answer_json.json --room_name room_312