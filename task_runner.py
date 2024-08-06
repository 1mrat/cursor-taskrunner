import re
import os
import time
from typing import List, Tuple
import replicate
import requests
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init()

def print_log(message: str):
    print(f"{Style.DIM}{message}{Style.RESET_ALL}")

def print_success(message: str):
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

def print_error(message: str):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def generate_image(prompt: str, filename: str) -> bool:
    """
    Generate an image using the Flux Schnell model from Replicate.
    """
    # Get the Replicate API token from environment variable
    api_token = os.environ.get('REPLICATE_API_TOKEN')
    if not api_token:
        print_error("Error: REPLICATE_API_TOKEN environment variable is not set.")
        return False
    
    # Set the API token for the Replicate client
    replicate.Client(api_token=api_token)

    # List of supported aspect ratios
    supported_aspect_ratios = [
        "1:1",
        "16:9",
        "21:9",
        "2:3",
        "3:2",
        "4:5",
        "5:4",
        "9:16",
        "9:21"
    ]
    # Extract aspect ratio from prompt if mentioned
    aspect_ratio = "16:9"  # Default aspect ratio
    aspect_ratio_match = re.search(r'aspect_ratio (\d+:\d+)', prompt, re.IGNORECASE)
    if aspect_ratio_match:
        extracted_ratio = aspect_ratio_match.group(1)
        if extracted_ratio in supported_aspect_ratios:
            aspect_ratio = extracted_ratio
        else:
            print_error(f"Unsupported aspect ratio '{extracted_ratio}' mentioned in prompt. Using default 9:16.")
    try:
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "num_outputs": 1,
                "output_format": "png"
                # "seed" is left unset unless provided
            }
        )
        
        # Check if the output is a list and contains at least one URL
        if isinstance(output, list) and len(output) > 0:
            image_url = output[0]
        else:
            print_error("Unexpected output format from Replicate API", output)
            return False
        
        # Download the image
        response = requests.get(image_url)
        if response.status_code == 200:
            # Check if the filename already exists
            base_name, extension = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filename):
                filename = f"{base_name}_{counter}{extension}"
                counter += 1
            with open(filename, 'wb') as f:
                f.write(response.content)
            print_log(f"Image generated and saved as: {filename}")
            return True
        else:
            print_error(f"Failed to download the image. Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error generating image: {str(e)}")
        return False

def parse_todo_file(file_path: str) -> List[Tuple[str, str, str]]:
    with open(file_path, 'r') as f:
        content = f.read()
    
    pattern = r'- \[ \] @image (.+): (.+)'
    matches = re.findall(pattern, content)
    return [(f"- [ ] @image {filename}: {prompt}", filename, prompt) for filename, prompt in matches]

def update_todo_file(file_path: str, completed_tasks: List[str]):
    with open(file_path, 'r') as f:
        content = f.readlines()
    
    updated_content = []
    for line in content:
        if any(task in line for task in completed_tasks):
            updated_content.append(line.replace('- [ ]', '- [x]'))
        else:
            updated_content.append(line)
    
    with open(file_path, 'w') as f:
        f.writelines(updated_content)

def process_tasks(todo_file: str):
    tasks = parse_todo_file(todo_file)
    completed_tasks = []

    for line, filename, prompt in tasks:
        if generate_image(prompt, filename):
            completed_tasks.append(line)
            print_success(f"Task completed: {filename} image created")
        else:
            print_error(f"Failed to complete task: {line.strip()}")

    if completed_tasks:
        update_todo_file(todo_file, completed_tasks)
        print_log(f"Updated {todo_file} with completed tasks.")
    else:
        print_log("No tasks were completed.")

def main():
    todo_file = 'TODO.md'
    last_modified = 0
    
    print_log(f"Monitoring {todo_file} for changes. Press Ctrl+C to stop.")
    
    try:
        while True:
            current_modified = os.path.getmtime(todo_file)
            if current_modified > last_modified:
                print_log(f"Changes detected in {todo_file}")
                process_tasks(todo_file)
                last_modified = current_modified
            time.sleep(1)
    except KeyboardInterrupt:
        print_log("Stopping task runner.")

if __name__ == "__main__":
    main()