import asyncio
from pydub import AudioSegment
from pydub.playback import play
import threading
from dotenv import load_dotenv
from llama_utils import *
from llama_utils import *
from imagine import *
import os, json, time
import numpy as np
import sys
load_dotenv()
URL = os.environ['URL']
KEY = os.environ['OPEN']
from playsound import playsound



base = (f'Transform the input you have been given into a reusable narrative scaffold with logical, symbolic and emotional bones.'
		f'Given this topic try to find its ethical center and form a set of observations that represent instances of the topic '
		f'and then either contradictory or polar opposite examples.')


class Visualizer:
	def __init__(self, song, lyrics: str, len=300,meaning='', pre_rendered=False):
		self.api = setup_client(URL)
		self.states = {'preprocess': 'deepseek-r1:8b',
					   'creative': 'gemma3:4b'}
		# load lyrics split into chunks
		self.name = lyrics
		self.lyrics = self.load_lyrics(lyrics)
		# TODO: start generating interpretations of narrative and imagery
		self.interpretations = []
		self.image_jobs = {}
		self.music = song
		self.pre_rendered = pre_rendered
		if not pre_rendered:
			self.build_interpretations(pre_rendered)
		# self.run(lyrics, runtime)
	
	
	def build_interpretations(self, has_images):
		meanings = {}
		image_dict = {}
		for i in range(len(self.lyrics)):
			excerpt = self.lyrics[i].replace('\n\n','\n').replace("â€”","")
			print(f'[~] Transforming lyrical excerpt {i}/{len((self.lyrics))}\n{excerpt}')
			interpretation = self.transform_lyrics(excerpt)
			trimmed = interpretation.split('[START]')[1].split('[END]')[0].replace("â€”","")
			meanings[excerpt] = trimmed
			self.interpretations.append(trimmed)
			if not has_images:
				key = self.create_visual(self.interpretations.pop())
				self.image_jobs[i] = key
			name_head = self.name.split('.')[0].replace(' ', '').lower()
			if not self.pre_rendered:
				if i in self.image_jobs.keys():
					uid =  self.image_jobs[i]
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
				filename = f'{name_head}_comfy_{i:2d}.png'
				if not self.pre_rendered:
					for fname in image_dict.keys():
						img_content = image_dict[fname]
						print(f'Saving {filename}')
						open(filename, 'wb').write(img_content)
		return meanings
	
	async def run(self, lyrics, runtime):
		timeout = round(runtime/len(lyrics))
		name_head = self.name.split('.')[0].replace(' ', '').lower()
		
		# await asyncio.sleep(10)
		for j in range(len(self.lyrics)):
			# now that all images are queued up lets retrieve em
			filename = f'{name_head}_comfy_{j:2d}.png'
			excerpt = self.lyrics[j].replace('\n\n', '\n')
			print(f' Sleeping for {timeout}')
			time.sleep(timeout/8)
		
	def load_lyrics(self, song_file):
		lyrics = []
		if not os.path.isfile(song_file):
			print(f'[X] cannot find {song_file}')
			return []
		with open(song_file, 'r') as f:
			raw_lyrics = f.readlines()
		n_lines = len(raw_lyrics)
		window = 8
		n_chunks = round(n_lines/window)
		for i in range(window*round(n_chunks)):
			lyrics.append('\n'.join(raw_lyrics[i:i+round(window)]))
		return lyrics
		
	def transform_lyrics(self, excerpt):
		condensed = excerpt.replace("\n","").replace("â€”","")
		lyrical = f'```\n{condensed}\n```'
		context = ('Transform the following song lyrics into a vivid visual scene, capturing its emotional tone,symbolic'
		           'meaning, and implied or explicitly defined setting. Avoid literal word for word depictions; instead, '
		           'create an evocative that feels like a dream memory of the lyrics. Choose the artistic tone and color'
		           'palette based on the *feeling* the lyrics convery.'
		           'Never include nudity or sexual themes in any way.\n'
		           f'**Lyrics**:{lyrical}\n')
		sd_magic = (f'**Stable Diffusion Prompt Output Format:**\n\n[START]"A [emotionally charged description] of [symbolic visual'
		            f' elements], in a [specific setting or atmosphere], illustrated in the style of [artistic tone], '
		            f'[lighting], [color palette choice], [composition keywords]."[END]')
		return ask_model(self.api, self.states['creative'], context + sd_magic).message.content
	
	def create_visual(self, stable_prompt):
		loras = '<lora:realism_lora_comfy_converted.safetensors:1> <lora:addDetail.safetensors:1>'
		# modularize specific loras based on stable_prompt keywords
		image_prompt = json.loads(open('ImageGeneration1.json', 'r').read())
		image_prompt['6']['inputs']['text'] = stable_prompt + loras
		print(f'\t\t~~ VISUALIZING ~~\n\n{stable_prompt}')
		result = queue_prompt(image_prompt)
		id = result['prompt_id']
		return id



def play_audio_nonblocking(path):
    def _play():
        audio = AudioSegment.from_file(path)
        play(audio)
    threading.Thread(target=_play, daemon=True).start()
def main():
	song = 'TheRedPhone.mp3'
	lyrics = f'{song.split(".")[0].replace(" ","_")}.txt'
	if len(sys.argv) > 1:
		song = f'{sys.argv[1].split(" ", "_")}.mp3'
		lyrics = sys.argv[1]
	see = Visualizer(song, lyrics, 220, '', False)
	asyncio.run(see.run(lyrics,245))

if __name__ == '__main__':
	main()
