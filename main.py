from composite_loader import load_all_archetypes_with_composites, CompositeCharacter
from historian import allegory_json_to_script, generate_graphic_novel_html
from typing import List
import time
from datetime import datetime
import characters
from imagine import *
from characters import load_archetypes, ArchetypeCharacter
from situations import load_situations, Situation
from dotenv import load_dotenv
from llama_utils import *
import random
import json
import os
import re

load_dotenv()
URL = os.environ['URL']


class RecursiveAllegory:
	def __init__(self, characters,context,settings):
		"""
		Engine Loop
		Narrator reads initial_prompt, sets stage
			Each archetype takes turns responding (random or weighted order)
			After each turn, system logs state (optional: summary or emotional state)
			System checks for exit condition:
			  - max turns reached
			  - Mirror or Synthesizer declares closure
			  - user interrupt

		Output is rendered: story, summary, graph, overlay, etc.
		"""
		self.narrator = characters[0]
		# include the characters from settings
		players = []
		if len(players):
			for c in characters:
				name = c.name
				if name in context.participants:
					players.append(c)
		else:
			n_players = random.randint(3,6)
			players = characters[1:n_players]
		self.characters = players
		self.journey = context
		self.rules = settings
		self.api = setup_client(URL)
		self.exited = False
		
		# map models to characters
		self.logical = 'gemma3:4b'
		self.default = 'gemma3:4b'
		# create a folder for this stories assets
		t = time.time()
		d = datetime.fromtimestamp(t)
		
		self.folder = os.path.join(os.getcwd(),
		                           f'myth_assets_{self.journey["title"].replace(" ","")}_'
		                           f'{d.month:02d}{d.day:02d}{d.year:02d}_{d.minute:02d}{d.hour:02d}{d.second:02d}')
		if not os.path.isdir(self.folder):
			os.mkdir(self.folder)

	def run(self):
		print(f'[+] Start {self.journey["title"]} [{len(self.characters)} Archetypes playing]')
		prompt = self.journey['seed']
		story = [{"Initial Seed": prompt}]
		max_recursion = self.rules['exit_conditions'][0]['value']
		round = 0
		try:
			while not self.exited and round < max_recursion:
				choices = {}
				next_character = self.characters[random.randint(0,len(self.characters)-1)]
				next_choice = self.build_character_prompt(next_character, prompt, story)
				character_action = ask_model(self.api, self.default, next_choice)
				print(f'\t\t\tITER {round:02d}\n"{next_character.name}":\n{character_action.message.content}')
				# Now what actually happens within the world given this characters choice
				narration = self.build_narrator_prompt(prompt, next_character, character_action.message.content, choices)
				# story.append({'character': next_character.name, 'Decision': character_action.message.content})
				# if round > 2 : self.exited = narrator_exit_check(narration)
				unchanged = True
				while unchanged:
					try:
						result = ask_model(self.api, self.default, narration)
						direct_result = result.message.content.split('</think>')[-1].split('[RESULT]')[1].split('[')[0]
						themes = result.message.content.split('</think>')[-1].split('[THEME]')[-1]
						prompt = direct_result
						# story.append({self.narrator.name: direct_result})
						round += 1
						unchanged = False
					except IndexError:
						direct_result = result.message.content.split('</think>')[-1].split('[')[0]
						unchanged = False
				# Now create the graphic for the story panel
				comfy_prompt = ask_model(self.api,self.logical,self.build_graphic_panel_prompt(f'Character:'
																							   f'\n{next_choice}\n'
																							   f'{direct_result}'))
				
				image_prompt = comfy_prompt.message.content.split('[PROMPT]')[-1].split('[')[0]
				emotions = comfy_prompt.message.content.split('[EMOTIONS]')[-1]
				print('*' * 10 + '| Generating Image |' + '*' * 10 + f'\n{image_prompt}\n' + '=' * 60)
				uid = create_visual(image_prompt, emotions)
				finished = False
				image_dict = {}
				while not finished:
					try:
						image_dict = find_images(uid)
					except KeyError:
						# time.sleep(5)
						pass
					if image_dict == {}:
						time.sleep(2)
					else:
						finished = True
				filename = f'{self.journey["title"].replace(" ","_")}_{uid}_comfy.png'
				story.append({'ImagePrompt': image_prompt,
							  'ImageResult': filename,
				              'Character': next_character.name,
				              'Narration': direct_result})
				# Create a labeled visual
				for fname in image_dict.keys():
					img_content = image_dict[fname]
					print(f'Saving {filename}')
					open(os.path.join(self.folder,filename), 'wb').write(img_content)
					add_caption_to_image(os.path.join(self.folder,filename),image_prompt,os.path.join(self.folder,filename.replace('comfy','caption')))
					# os.remove(os.path.join(self.folder,filename))
				open(os.path.join(self.folder,'StoryBook.json'),'w').write(json.dumps(story,indent=2))
				print('=' * 80)
		except KeyboardInterrupt:
			self.exited = True
		return story
	
	def build_character_prompt(self, character:characters.ArchetypeCharacter, current_prompt:str, history:dict):
		backstory = (f'You are the character in a turn based adventure game. You will be given a CONFLICT and you must try'
					 f'to solve or react to the given situation using the traits and role of your character.\n')
		summ = ''
		if len(history) > 1:
			summ = ('Here is the history of prior choices made by characters in the game, and the actions taken by the narrator.'
					'Please incorporate the following history of prior choices into your decision making process.\n'
					'Overall you want to resolve the conflict. If that means evolving as a character thats fine. Do not '
					'ignore the other participants. By working together you might succeeed. This is a difficult quest, '
					'and *learning from eachother* just might be the key. [HISTORY]\n')
			for entry in history:
				k = entry.keys()
				if 'Agent' in k:
					summ += f'\n{entry["Agent"]}: {entry["Decision"]}\n' + '=' * 40
				else:
					summ += f'\n{list(k)[-1]}:\n{entry[list(k)[-1]]}\n' + '=' * 40
		skills = '\n\t- ' + '\n\t-'.join(character.role.split(","))
		tonal = '\n\t-'.join(character.tone)
		prompt = f'[BACKSTORY]\n{backstory + summ}\n[YOUR CHARACTER: "{character.title}"]\nArchetype:{character.name}\nSkills/Weaknesses:\n{skills}\n'
		prompt += f'Character Traits/Tone:\n{tonal}\nCore Beliefs/Drive: {character.system_prompt}\n'
		prompt += f'\nGiven this rich backstory reply as "{character.name}" given the following situation you are in:\n'
		prompt += f'Situation:\n{current_prompt}'
		return prompt
	
	
	def build_narrator_prompt(self, current_prompt, player, choice, history):
		narrator_goals = '\n\t-'.join(self.narrator.core_functions)
		context = (f'You are the narrator and "dungeon master" like authority for a turn based game that will be occurring '
				   f'between several players. You will be given the context of the current "journey" the players find themselves in.'
				   f'Your job is to look at what all the players have chosen given the overal goal and their current state, '
				   f'and determine how their choices will interact with eachother and the conflict they are trying to solve'
				   f'and progress the story forward in a meaningful way, ideally for them to make a transformative discovery'
				   f'about the themes the meant to be grappled with or by achieving the "End Goal" I will define.\n'
				   f'I will first provide you with the context of the "journey" the players are navigating: \n')
		backstory = f'[BACKSTORY]\nTitle: {self.journey["title"]}\nStory Seed: \n{" ".join(self.journey["seed"])}]\n'
		backstory += f'Your Goals:{narrator_goals}\n'
		prompt = f'[CONTEXT]\n{context}\n{backstory}**Current State** \n{current_prompt}\nNext Player:{player.name}\n'
		skills = '\n\t- ' + '\n\t-'.join(player.role.split(","))
		tonal = '\n\t-'.join(player.tone)
		prompt += f'\nPlayer Traits:\n{tonal}\nTheir Skills:\n{skills}\n'
		prompt += (f'\nGiven all this context and information please operator as the narrator and consider how the story will progress'
				   f'given the players actions and all given context. Please provide the result following [RESULT].\n'
				   f'If relevant to the decision/consequence include any motifs of this interaction followinig [THEME].')
		return prompt

	def build_graphic_panel_prompt(self, current_prompt):
		base = (f'Distill the following piece of a dramatic screenplay into a single descriptive snapshot. We need to '
				f'distill everything into a single paragraph that captures the essence and meaning along with the setting'
				f'and characters. Here is the given storyline script:\n')
		prompt = (f'{base}\n```{current_prompt}\n```\nPlease Reply with the description following a [PROMPT] label. And '
				  f'after that please attempt to identify the main emotion of the script excerpt above following the label'
				  f'[EMOTIONS].\n')
		return prompt

def narrator_exit_check(narrator_output: str) -> bool:
	"""
	Checks the narrator's output for symbolic or poetic closure signals
	indicating the simulation should exit.
	"""
	closing_signals: List[str] = [
		"the silence lingers",
		"no one responds",
		"the fire dies down",
		"their voices fall away",
		"they leave it there",
		"the story has shaped itself",
		"nothing more is said",
		"the circle breaks",
		"it ends as it began",
		"the last ember fades"
	]

	narrator_output_lower = narrator_output.lower()
	return any(phrase in narrator_output_lower for phrase in closing_signals)


def find_occurences(pattern, text):
	indices = []
	start_index = 0
	finds = []
	while True:
	    index = text.find(pattern, start_index)
	    if index == -1:
	        break
	    indices.append(index)
	    if start_index !=0:
		    finds.append(text[start_index:index])
	    start_index = index + len(pattern)
		
	return finds
def create_visual(stable_prompt, emotions):
	# change style based on emotions
	loras = (',(Vibrant Colors),Moebius Style:0.5,Frank Miller Style:0.5, <lora:Comic book V2.safetensors:1> , '
	         'highly detail, 4K, cinematic lighting, award winning composition, ')
	mappers = {'sad':['sad','melancholy'],
	           'anger':['rage','anger'],
	           'wonder':['awe','wonder','amaze','surreal','dream'],
	           'scary':['fear','unsettling','eerie','frightening','ominous']}
	moods = {'sad': 'camera distant, side profile or downward, (Indie Sketch),Minimal lines and faded tones with emotional isolation.',
	         'anger': 'gritty street art style, graffiti punk, Bold lines and harsh textures like protest art or underground zines.',
	         'wonder':'(Cosmic Surreal),Rich colors and scale-bending imagery evoking awe and dream logic.',
	         'scary':'(unsettling),gothic,High-contrast with heavy shadows and claustrophobic framing.'}
	feelings = find_occurences('**', emotions)
	for feeling in feelings:
		for emotion in list(mappers.keys()):
			if feeling in mappers[emotion]:
				loras += f'{moods[emotion]}'
	# modularize specific loras based on stable_prompt keywords
	image_prompt = json.loads(open('ComicRealism.json', 'r').read())
	image_prompt['6']['inputs']['text'] = stable_prompt + loras
	# TODO: change model based on emotions too?
	
	result = queue_prompt(image_prompt)
	id = result['prompt_id']
	return id

from PIL import Image, ImageDraw, ImageFont
import os

def add_caption_to_image(image_filename, caption_text, output_path=None):
	"""
	Adds a caption as a subtitle to the bottom of an image.

	Parameters:
	- image_filename: str, path to the input image file.
	- caption_text: str, the text to place below the image.
	- output_path: str, path to save the output image. If None, saves with '_captioned' suffix.

	Returns:
	- output image path
	"""
	# Load the image
	image = Image.open(image_filename).convert("RGB")

	# Define font and caption space
	font_size = 17
	try:
		font = ImageFont.truetype("arial.ttf", font_size)
	except IOError:
		font = ImageFont.load_default()

	# Create a new image with space for the caption
	margin = 10
	caption_lines = caption_text
	lines = wrap_caption_to_lines(caption_lines, 100)
	caption_height = (font_size + margin) * round(len(lines)*1.25) + margin * 2

	new_image = Image.new("RGB", (image.width, image.height + caption_height), "black")
	new_image.paste(image, (0, 0))

	
	# Draw the caption
	draw = ImageDraw.Draw(new_image)
	y_text = image.height + margin
	for line in lines:
		text_width, text_height = draw.textbbox((0, margin),line,font=font)[2:]
		x_text = (image.width - text_width) / 2
		draw.text((x_text, y_text), line, font=font, fill="white")
		y_text += text_height
		

	# Save the result
	if not output_path:
		base, ext = os.path.splitext(image_filename)
		output_path = f"{base}_captioned{ext}"
	new_image.save(output_path)

	return output_path


def wrap_caption_to_lines(caption, line_length=50):
    """
    Splits a long caption string into a list of lines, each no longer than line_length characters,
    without breaking words across lines.

    Parameters:
    - caption: str, the full text to wrap
    - line_length: int, max characters per line

    Returns:
    - List of strings, each a wrapped line
    """
    words = caption.split()
    lines = []
    current_line = ""

    for word in words:
        # Check if adding the next word would exceed the limit
        if len(current_line) + len(word) + (1 if current_line else 0) <= line_length:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def main():
	"""
	Bonus Features to Extend Later:

	entropy_level (chaotic vs ordered recursion)
	memory_mode (e.g., do archetypes remember each other? persist influence?)
	archetype_bias (weighting toward poetic vs skeptical lens)
	player_override (user can inject choices mid-loop)
	emergent_tags (system detects motifs as they recur)
	"""
	# Load Characters
	cwd = os.getcwd()
	base_character_folder = os.path.join(cwd,'archetypes','base')
	composite_character_folder = os.path.join(cwd, 'archetypes', 'composite')
	characters = load_archetypes(base_character_folder)
	complex_characters = load_all_archetypes_with_composites(composite_character_folder)
	narrator = characters[0]
	for character in list(complex_characters):
		characters.append(character)
	
	
	# TODO: customize characters
	cast = characters
	
	# Load Settings and Configuration for current simulation
	scenes = 'story_seeds.json'
	# context = load_situations(scenes)
	stories = load_situations(scenes)
	titles = list(stories.keys())
	titles = ['The Signal Garden','The Signal Garden','The Signal Garden','The Signal Garden','The Signal Garden',
	          'The Signal Garden','The Signal Garden','The Signal Garden','The Signal Garden','The Signal Garden']
	random.shuffle(titles)
	for story_name in titles:
		random.shuffle(characters)
		characters.remove(narrator)
		characters.insert(0,narrator)
		example = stories[story_name]
		settings = json.loads(open('end_states.json','r').read())
		
		print(f'[+] {len(characters)} Archetype Characters Loaded')
		
		# Run Simulation
		print(f'[#] Running Simulation of "{story_name}"')
		rap = RecursiveAllegory(cast, {'title':story_name,'seed':example}, settings)
		story = rap.run()
		t = time.time()
		d = datetime.fromtimestamp(t)
		file_in = f'comicbook_{d.month:02d}{d.day:02d}{d.year}_{story_name.replace(" ","")}.json'
		file_out = file_in.split('.')[0] + '_comic.json'
		open(os.path.join(rap.folder,file_out),'w').write(json.dumps(story,indent=2))
		try:
			script = os.path.join(rap.folder,'script.md')
			allegory_json_to_script(json.loads(open(os.path.join(rap.folder,file_out), 'r').read()), script)
			generate_graphic_novel_html(script, rap.folder, os.path.join(rap.folder,f'{story_name.replace(" ","")}.html'), title=story_name)
		except:
			pass


if __name__ == '__main__':
	main()
