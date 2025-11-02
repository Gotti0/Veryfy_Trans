import logging

def parse_log(file_path):
    """ 
    Parses a log file where each line is a sentence.
    Returns a list of non-empty, stripped sentences.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read all lines, strip whitespace, and filter out empty lines
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.warning(f"Parser: Log file not found at {file_path}")
        return []
    except Exception as e:
        logging.error(f"Parser: An error occurred while parsing {file_path}: {e}")
        return []