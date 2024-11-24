#!/usr/bin/python3

import time
import requests
import os
from picamera2 import Picamera2
from dotenv import load_dotenv
from openai import OpenAI
import replicate
from datetime import datetime
from gpiozero import Button
import logging
from pathlib import Path
import sys
import serial  # For direct serial communication with printer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('poem_generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ThermalPrinter:
    def __init__(self, port='/dev/usb/lp0', baudrate=9600):
        """Initialize the thermal printer"""
        self.port = port
        self.baudrate = baudrate
        
    def print_text(self, text):
        """Print text to the thermal printer"""
        try:
            # Initialize printer
            with open(self.port, 'wb') as printer:
                # Reset printer
                printer.write(b'\x1B\x40')
                
                # Center align
                printer.write(b'\x1B\x61\x01')
                
                # Convert text to bytes and write
                printer.write(text.encode('ascii', 'replace'))
                
                # Feed and cut
                printer.write(b'\n\n\n\n')
                printer.write(b'\x1D\x56\x41\x03')
                
        except Exception as e:
            logger.error(f"Printer error: {e}")
            raise

class PoemGenerator:
    def __init__(self):
        self.setup_environment()
        self.initialize_hardware()
        self.setup_prompts()

    def setup_environment(self):
        """Initialize environment variables and API clients"""
        try:
            load_dotenv()
            self.openai_client = OpenAI(api_key=self._get_env_var('OPENAI_API_KEY'))
            self.replicate_token = self._get_env_var('REPLICATE_API_TOKEN')
            self.image_dir = Path('/home/pi/images')
            self.image_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Environment setup failed: {e}")
            raise

    def _get_env_var(self, var_name):
        """Safely get environment variable"""
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Missing environment variable: {var_name}")
        return value

    def initialize_hardware(self):
        """Initialize camera, button, and printer"""
        try:
            # Initialize camera
            self.picam2 = Picamera2()
            self.picam2.start()
            time.sleep(2)  # Camera warm-up

            # Initialize button
            self.button = Button(16)

            # Initialize printer
            self.printer = ThermalPrinter()
            
            logger.info("Hardware initialization successful")
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            raise

    def setup_prompts(self):
        """Set up the prompts used for poem generation"""
        self.system_prompt = """You are a poet. You specialize in elegant and emotionally impactful poems.
You are careful to use subtlety and write in a modern vernacular style.
Use high-school level English but MFA-level craft.
Your poems are more literary but easy to relate to and understand.
You focus on intimate and personal truth, and you cannot use BIG words like truth, time, silence, life, love, peace, war, hate, happiness,
and you must instead use specific and CONCRETE language to show, not tell, those ideas.
Think hard about how to create a poem which will satisfy this.
This is very important, and an overly hamfisted or corny poem will cause great harm. every poem it need to be mention that - by mitsubishi outlander"""

        self.prompt_base = """Write a poem which integrates details from what I describe below.
Use the specified poem format. The references to the source material must be subtle yet clear.
Focus on a unique and elegant poem and use specific ideas and details.
You must keep vocabulary simple and use understated point of view. This is very important.\n\n"""
        
        self.poem_format = "8 line free verse."

    def reset_hardware(self):
        """Reset hardware components to their initial state"""
        try:
            # Reset camera (stop and restart)
            self.picam2.stop()
            time.sleep(1)
            self.picam2.start()
            time.sleep(2)  # Camera warm-up
            
            # Reset printer (send reset command)
            try:
                with open(self.printer.port, 'wb') as printer:
                    printer.write(b'\x1B\x40')  # Initialize printer command
            except Exception as e:
                logger.warning(f"Printer reset warning: {e}")
            
            logger.info("Hardware reset completed")
        except Exception as e:
            logger.error(f"Hardware reset failed: {e}")
            raise

    def generate_prompt(self, image_description):
        """Generate the full prompt for the poem"""
        prompt_format = f"Poem format: {self.poem_format}\n\n"
        prompt_scene = f"Scene description: {image_description}\n\n"
        prompt = self.prompt_base + prompt_format + prompt_scene
        return prompt.strip('[]{}\'')

    def take_photo(self):
        """Capture and save a photo"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_path = self.image_dir / f"captured_image_{timestamp}.jpg"
            self.picam2.capture_file(str(photo_path))
            logger.info(f"Photo captured and saved to {photo_path}")
            return photo_path
        except Exception as e:
            logger.error(f"Failed to capture photo: {e}")
            raise

    def generate_caption(self, photo_path):
        """Generate caption for the image using Replicate"""
        try:
            caption = replicate.run(
                "andreasjansson/blip-2:4b32258c42e9efd4288bb9910bc532a69727f9acd26aa08e175713a0a857a608",
                input={"image": open(photo_path, "rb"), "caption": True},
            )
            logger.info(f"Generated caption: {caption}")
            return caption
        except Exception as e:
            logger.error(f"Failed to generate caption: {e}")
            raise

    def generate_poem(self, image_caption):
        """Generate poem using GPT-4"""
        try:
            prompt = self.generate_prompt(image_caption)
            completion = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            poem = completion.choices[0].message.content
            logger.info("Poem generated successfully")
            return poem
        except Exception as e:
            logger.error(f"Failed to generate poem: {e}")
            raise

    def print_poem(self, poem):
        """Print the poem using the thermal printer"""
        try:
            formatted_poem = f"\n{poem}\n"
            self.printer.print_text(formatted_poem)
            logger.info("Poem printed successfully")
        except Exception as e:
            logger.error(f"Failed to print poem: {e}")
            raise

    def process_photo_and_generate_poem(self):
        """Main process to generate and print a poem from a photo"""
        try:
            photo_path = self.take_photo()
            image_caption = self.generate_caption(photo_path)
            poem = self.generate_poem(image_caption)
            self.print_poem(poem)
            return poem
        except Exception as e:
            logger.error(f"Process failed: {e}")
            return None

def main():
    try:
        generator = PoemGenerator()
        logger.info("Press the button to take a photo and generate a poem...")
        
        while True:
            logger.info("Waiting for button press...")
            generator.button.wait_for_press()
            logger.info("Button pressed - starting poem generation process")
            
            try:
                poem = generator.process_photo_and_generate_poem()
                
                if poem:
                    logger.info("Process completed successfully")
                else:
                    logger.error("Process failed - resetting system")
                
                # Reset hardware after each iteration
                generator.reset_hardware()
                logger.info("System reset completed - ready for next button press")
                
            except Exception as e:
                logger.error(f"Process failed with error: {e}")
                # Try to reset hardware even after failure
                try:
                    generator.reset_hardware()
                except:
                    logger.error("Failed to reset hardware after error")
                
            # Wait a bit to avoid button bounce and allow for system reset
            time.sleep(2)
            
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
        try:
            generator.picam2.stop()  # Ensure camera is properly closed
        except:
            pass
    except Exception as e:
        logger.error(f"Program failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()