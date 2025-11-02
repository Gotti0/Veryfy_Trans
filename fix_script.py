import argparse
import logging
import sys
from log_parser import parse_log

def create_replacement_map(proof_log_path, translated_log_path):
    """Parses the log files to create a map of original lines to translated lines."""
    logging.info(f"Parsing logs to create replacement map.")
    
    original_lines = parse_log(proof_log_path)
    translated_lines = parse_log(translated_log_path)

    if not original_lines or not translated_lines:
        logging.error("One or both log files could not be parsed or are empty.")
        return None

    replacements = {orig: trans for orig, trans in zip(original_lines, translated_lines)}
    return replacements

def main():
    """Main function to read, replace, and write the file using command-line arguments."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("fix_script.log", mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    parser = argparse.ArgumentParser(
        description="Replace text in a target file based on original and translated log files."
    )
    parser.add_argument(
        "proof_log",
        help="Path to the original proof log file (e.g., 'language_proof.log')"
    )
    parser.add_argument(
        "translated_log",
        help="Path to the translated proof log file (e.g., 'language_proof_translated.log')"
    )
    parser.add_argument(
        "target_file",
        help="Path to the target text file to modify"
    )
    args = parser.parse_args()
    
    logging.info("Script started.")
    logging.info(f"Target file: {args.target_file}")

    replacements = create_replacement_map(args.proof_log, args.translated_log)

    if not replacements:
        logging.error("Could not create replacement map. Exiting.")
        return

    try:
        logging.info(f"Reading target file: {args.target_file}")
        with open(args.target_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"Target file not found at {args.target_file}")
        return

    logging.info(f"Starting replacement process...")
    logging.info(f"Found {len(replacements)} replacement rules.")

    original_content = content
    modified_count = 0
    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            modified_count += 1
    
    if original_content == content:
        logging.info("No changes were made. The file content might already be up to date.")
    else:
        try:
            with open(args.target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"File modification successful. {modified_count} replacements were made.")
        except Exception as e:
            logging.error(f"Error writing to file: {e}")

    logging.info("Script finished.")

if __name__ == "__main__":
    main()