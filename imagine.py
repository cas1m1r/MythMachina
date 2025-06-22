from dotenv import load_dotenv
import websocket
import urllib.request
import urllib

import uuid
import json
import os

load_dotenv()
URL = os.getenv('URL')
comfy = os.getenv('COMFY')

client_id = str(uuid.uuid4())  # Generate a unique client ID
ws = websocket.WebSocket()
ws.connect(f"ws://{comfy}:8188/ws?clientId={client_id}")

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{comfy}:8188/history/{prompt_id}") as response:
        return json.loads(response.read())

def queue_prompt(prompt):
	# generic image creation
	p = {"prompt": prompt, "client_id": client_id}
	data = json.dumps(p).encode('utf-8')
	req = urllib.request.Request(f"http://{comfy}:8188/prompt", data=data)
	return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{comfy}:8188/view?{url_values}") as response:
        return response.read()

def find_images(prompt_id):
	# Since a ComfyUI workflow may contain multiple SaveImage nodes,
	# and each SaveImage node might save multiple images,
	# we need to iterate through all outputs to collect all generated images
	output_images = {}
	history = get_history(prompt_id)
	node_output = history[prompt_id]['outputs']
	images_output = {}
	for key in node_output.keys():
		fields = node_output[key]
		if 'images' in fields:
			for image in node_output[key]['images']:
				image_data = get_image(image['filename'], image['subfolder'], image['type'])
				images_output[image['filename']] = image_data
			output_images[prompt_id] = images_output
	return images_output
	
def main():
	prompt = json.loads(open('imageGeneration.json', 'r').read())
	# Get prompt_id for tracking the execution
	
	image_description = prompt['6']['inputs']['text']
	
	prompt_id = queue_prompt(prompt)['prompt_id']
	images = find_images(prompt_id)
	
	for fname in images.keys():
		image_data = images[fname]
		print(f'Saving {fname}')
		open(fname,'wb').write(image_data)
	


if __name__ == '__main__':
	main()







