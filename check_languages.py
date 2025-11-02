# -*- coding: utf-8 -*-
import logging
import re
import os
import argparse
import json



def load_replacements(file_path="replacements.json"):
    """Loads replacement rules from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Could not load or parse replacements file {file_path}: {e}")
        return {}

def check_languages(file_path, log_file):
    """
    Checks a text file for Japanese and Chinese characters and logs the findings.
    """
    # Basic logging for script execution status, not for sentence output.
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Regex for Japanese (Hiragana/Katakana) and Chinese (Hanzi/Kanji)
    japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]+')
    chinese_pattern = re.compile(r'[\u4E00-\u9FFF]+')

    found_language = False
    logging.info(f"Starting language check on file: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        replacements = load_replacements()

        # Apply custom replacements first
        for old, new in replacements.items():
            content = content.replace(old, new + ' ')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info("File content has been modified with custom replacements.")

        final_lines = content.split('\n')
        
        # Open the log file to write the sentences found.
        with open(log_file, 'w', encoding='utf-8') as log_f:
            for line in final_lines:
                # Exclude text within parentheses
                line_to_check = re.sub(r'\(.*?\)', '', line)

                if japanese_pattern.search(line_to_check) or chinese_pattern.search(line_to_check):
                    log_f.write(line.strip() + '\n')
                    found_language = True

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return

    if not found_language:
        logging.info("No Japanese or Chinese characters were found in the file.")
    else:
        logging.info(f"Language check finished. Results logged to {log_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Checks a text file for Japanese and Chinese characters.")
    parser.add_argument("file_path", help="The path to the text file to check.")
    parser.add_argument("-l", "--log_file", default="language_check.log", help="The path to the log file. Defaults to language_check.log")
    
    args = parser.parse_args()

    check_languages(args.file_path, args.log_file)
