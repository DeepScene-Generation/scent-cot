import os
import json
import base64
import numpy as np
import re
import ast
from openai import OpenAI
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from scene_utils.utils import check_constraints, check_collisions
from render_utils.render import render_blender
import time
import threading
ASSETS_PATH = '/wuhu_uni_ai/limingsheng/rllm/Assets'
import traceback
client = OpenAI(
    api_key="xxx",
    base_url="xxx"
)

# Example JSON format for the response
example_json = """
{
  "realism_and_3d_geometric_consistency": {
    "grade": 8,
    "comment": "The renders appear to have appropriate 3D geometry and lighting that is fairly consistent with real-world expectations. The proportions and perspective look realistic."
  },
  "functionality_and_activity_based_alignment": {
    "grade": 7,
    "comment": "The room includes a workspace, sleeping area, and living area as per the user preference. The L-shaped couch facing the bed partially meets the requirement for watching TV comfortably. However, there does not appear to be a TV depicted in the render, so it's not entirely clear if the functionality for TV watching is fully supported."
  },
  "layout_and_furniture": {
    "grade": 7,
    "comment": "The room has a bed that's not centered and with space at the foot, and a large desk with a chair. However, it's unclear if the height of the bed meets the user's preference, and the layout does not clearly show the full-length mirror in relation to the wardrobe, so its placement in accordance to user preferences is uncertain."
  },
  "color_scheme_and_material_choices": {
    "grade": 9, adheres to a light color scheme with blue and white tones as preferred by the user, without a nautical feel. The bed and other furniture choices are aligned with the color scheme specified."
  },
  "overall_aesthetic_and_atmosphere": {
    "grade": 8,
    "comment": "The room's general aesthetic is bright, clean, and relatively minimalistic, which could align with the user's preference for a light color scheme and a modern look. The chandelier is present as opposed to bright, hospital-like lighting."
  }
}
"""

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string

def vlm_evaluate_rooms(base64_image_1, base64_image_2, base64_image_3, base64_image_4, user_preference, room_name, num_evaluations=1):
    """
    Evaluates room renders based on user preferences and returns scores.
    
    Args:
        image_paths: List of paths to room render images (typically 2)
        user_preference: User's text description of preferred room
        size_of_room: Size of the room
        num_evaluations: Number of times to run evaluation for averaging
    
    Returns:
        Dictionary containing evaluation scores with means and standard deviations
        The complete response from the final evaluation
    """
    # # Prepare the evaluation prompt
    # evaluation_prompt = f"""
    # Give a grade from 1 to 10 or unknown to the four perspective renderings of the same room based on how well they collectively correspond to the user preference (in triple backquotes) in the following aspects:
    # - Realism and 3D Geometric Consistency
    # - Functionality and Activity-based Alignment
    # - Layout and furniture  
    # - Color Scheme and Material Choices
    # - Overall Aesthetic and Atmosphere         
    # User Preference:
    # ```{user_preference}```
    # Return the results in the following JSON format:
    # ```json
    # {example_json}
    # ```
    # """

    evaluation_prompt = f"""
    Evaluate four perspective renderings of the same room based on how well they collectively correspond to the user preference (in triple backquotes). 
    
    Note: For each perspective view, the ceiling and two walls in the current field of view have NOT been visualized (to avoid occluding objects in the scene). Please keep in mind these structural elements exist even though they are not visible in the renders.
    
    For each aspect below, give a grade from 1-10 with detailed justification:
    1. Realism and 3D Geometric Consistency: Assess whether the 3D geometry, proportions, perspective, and lighting appear physically realistic and consistent with real-world expectations across all views.
    2. Functionality and Activity-based Alignment: Evaluate whether the room fully satisfies all specified activities (workspace, sleeping area, living area) with object diversity and richness. The scene must include at least three distinct objects directly supporting each activity (e.g., desk+chair+lamp for workspace, bed+nightstand+wardrobe for sleeping area, couch+coffee table+TV for living area). Deduct points if total visible objects (excluding ceiling, floor, and walls) in the scene are fewer than 3.
    3. Layout and Furniture: Check if furniture placement matches preferences (bed not centered with space at foot, full-length mirror placement relative to wardrobe). Assess whether furniture dimensions and spatial relationships meet practical requirements.
    4. Color Scheme and Material Choices: Verify adherence to specified color scheme (light colors with blue/white tones) and absence of prohibited styles (no nautical theme). Evaluate material choices for furniture and surfaces in relation to the desired aesthetic.
    5. Overall Aesthetic and Atmosphere: Assess the general ambiance, including lighting style (preferably not hospital-like), decorative elements, and whether it achieves the desired modern, clean, and minimalistic look with bright atmosphere.

    User Preference:
    ```{user_preference}```

    Return the results in the following JSON format:
    ```json
    {example_json}
    ```
    """

    # Initialize grades dictionary for tracking scores
    grades = {
        "realism_and_3d_geometric_consistency": [],
        "functionality_and_activity_based_alignment": [],
        "layout_and_furniture": [],
        "color_scheme_and_material_choices": [],
        "overall_aesthetic_and_atmosphere": []
    }
    
    last_response = None
    
    # Run multiple evaluations to get a more reliable score
    for _ in range(num_evaluations):
        completion = client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": evaluation_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image_1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image_2}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image_3}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image_4}"}},
                ]}
            ],
            temperature=0.0
        )
        response_text = completion.choices[0].message.content
        last_response = response_text
        
        pattern = r'```json(.*?)```'
        matches = re.findall(pattern, response_text, re.DOTALL)
        json_content = matches[0].strip() if matches else None
        # print('--------------------------------')
        # print('json_content', json_content)
        # print('--------------------------------')
        # input('continue???')
        actual_string = ast.literal_eval(f"'''{json_content}'''")
        if json_content is None:
            try:
                grading = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"Error parsing response: {response_text}")
                continue
        else:
            try:
                grading = json.loads(actual_string)
                # print('grading', grading)
                # input('continue???')
            except json.JSONDecodeError:
                print(f"Error parsing JSON content: {actual_string}")
                continue
                
        # Collect grades for each category
        for key in grades:
            if key in grading and "grade" in grading[key] and isinstance(grading[key]["grade"], (int, float)):
                grades[key].append(grading[key]["grade"])
    
    # Calculate mean and standard deviation for each category
    results = {}
    for key in grades:
        if grades[key]:  # Check if we have any valid grades
            results[key] = {
                "mean": round(sum(grades[key])/len(grades[key]), 2), 
                "std": round(np.std(grades[key]), 2)
            }
        else:
            results[key] = {"mean": 0, "std": 0}
    
    # Generate output filename based on first image path
    output_name = os.path.join(ASSETS_PATH, room_name, 'qwen_turbo_grades.json')

    
    # Save results to JSON file
    with open(output_name, "w") as f:
        json.dump(results, f, indent=2)
    # print('--------------------------------')
    # print('results', results)
    # print('--------------------------------')
    return results, last_response





def extract_json_from_text(text):
    pattern = r"<answer>\s*(.*?)\s*</answer>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            return None
    else:
        return None
    
def metaverse_format_reward(predict_str: str) -> float:
    pattern = re.compile(r"^\s*<think>.*?</think>\s*<answer>.*?</answer>\s*$", re.DOTALL)
    format_match = re.fullmatch(pattern, predict_str)
    if not format_match:
        return None, 0
    answer_json = extract_json_from_text(format_match.group(0))
    if answer_json is None:
        return None, 0.1
    return answer_json, 0.5

def scene_reward(answer_json, user_preference, retrieval, extra_info):
    
    with threading.Lock():
        room_name = 'room_' + str(extra_info['index'])
        
        try:
            answer_json = retrieval.retrieve_assets(answer_json, room_name)
        except Exception as e:
            print(f'Error retrieving assets: {e}')
            try:
                collision_reward = 1 - check_collisions(answer_json)
            except Exception as e:
                print(f"Error checking collisions: {e}")
                collision_reward = 0

            try:
                constraint_reward = 1 - check_constraints(answer_json)
            except Exception as e:
                print(f"Error checking constraints: {e}")
                constraint_reward = 0

            return 0.0, collision_reward, constraint_reward
                
       
        try:
            collision_reward = 1 - check_collisions(answer_json)
        except Exception as e:
            print(f"Error checking collisions: {e}")
            collision_reward = 0


        try:
            constraint_reward = 1 - check_constraints(answer_json)
        except Exception as e:
            print(f"Error checking constraints: {e}")
            print(traceback.format_exc())  
            constraint_reward = 0

            
        json_file = os.path.join(ASSETS_PATH, room_name, 'answer_json.json')
        output_name = os.path.join(ASSETS_PATH, room_name, 'grades.json')
        try:
            os.system(f'python rllm/render_utils/render.py --json_file {json_file} --room_name {room_name}')
        
            image_path_1 = os.path.join(ASSETS_PATH, room_name, '1.png')
            image_path_2 = os.path.join(ASSETS_PATH, room_name, '2.png')
            image_path_3 = os.path.join(ASSETS_PATH, room_name, '3.png')
            image_path_4 = os.path.join(ASSETS_PATH, room_name, '4.png')

            base64_image_1 = image_to_base64(image_path_1)
            base64_image_2 = image_to_base64(image_path_2)
            base64_image_3 = image_to_base64(image_path_3)
            base64_image_4 = image_to_base64(image_path_4)



            vlm_reward, last_response = vlm_evaluate_rooms(base64_image_1, base64_image_2, base64_image_3, base64_image_4, user_preference, room_name)
            vlm_final_reward = (int(vlm_reward['overall_aesthetic_and_atmosphere']['mean']) + int(vlm_reward['color_scheme_and_material_choices']['mean']) + int(vlm_reward['layout_and_furniture']['mean']) + int(vlm_reward['functionality_and_activity_based_alignment']['mean']) + int(vlm_reward['realism_and_3d_geometric_consistency']['mean'])) / 50
        
            with open(output_name, 'w') as f:
                grades = {
                    "format_reward": 0.5,
                    "vlm_scores": {
                        "overall_aesthetic_and_atmosphere": vlm_reward['overall_aesthetic_and_atmosphere']['mean'],
                        "color_scheme_and_material_choices": vlm_reward['color_scheme_and_material_choices']['mean'],
                        "layout_and_furniture": vlm_reward['layout_and_furniture']['mean'],
                        "functionality_and_activity_based_alignment": vlm_reward['functionality_and_activity_based_alignment']['mean'],
                        "realism_and_3d_geometric_consistency": vlm_reward['realism_and_3d_geometric_consistency']['mean'],
                        "final_vlm_score": vlm_final_reward
                    },
                    "collision_score": collision_reward,
                    "constraint_score": constraint_reward,
                    "vlm_response": last_response
                }
                
                json.dump(grades, f, indent=2)
            return vlm_final_reward, collision_reward, constraint_reward
            
        except Exception as e:
            print(f'Error rendering: {e}')
            with open(output_name, 'w') as f:
                grades = {
                    "format_reward": 0.5,
                    "vlm_scores": 0,
                    "collision_score": collision_reward,
                    "constraint_score": constraint_reward,
                }
                json.dump(grades, f, indent=2)
            return 0.0, collision_reward, constraint_reward

            

    
   

def rllm_reward_fn_scene(data_source, predict_str, extra_info: dict, retrieval=None, **kwargs) -> float:

    user_preference = extra_info['user']


    answer_json, format_reward = metaverse_format_reward(predict_str)
    

    
    if format_reward == 0.5:
        vlm_final_reward, collision_reward, constraint_reward = scene_reward(answer_json, user_preference, retrieval, extra_info)
    else:
        print("Only format_reward", format_reward)
        return format_reward
    

    print("--------------------------------")
    print("format_reward", format_reward)
    print('vlm_final_reward', vlm_final_reward)
    print('collision_reward', collision_reward)
    print('constraint_reward', constraint_reward)
    print("--------------------------------")
    
    return format_reward + vlm_final_reward  + collision_reward + constraint_reward
    # return format_reward + vlm_final_reward
    # return format_reward + collision_reward + constraint_reward
    # return gpt4_final_reward / 50 + 0.5*format_reward - 0.2*collision_ratio - 0.2*constraint_ratio

